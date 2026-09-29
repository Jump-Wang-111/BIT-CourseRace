import unittest
import threading
from email.utils import formatdate
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

import requests

import CourseRace as app


class CourseRaceTests(unittest.TestCase):
    def setUp(self):
        app.stop_event.clear()
        app.login_expired.clear()
        app.stop_reason = None
        self.course = {"bjdm": "test", "lx": "0", "csrfToken": ""}
        app.status["test"] = {"bjmc": "test", "success": 0, "fail": 0}

    def tearDown(self):
        app.stop_event.clear()
        app.login_expired.clear()
        app.stop_reason = None
        app.status.clear()

    def response(self, text='{"code": 0}', status=200):
        response = requests.Response()
        response.status_code = status
        response._content = text.encode()
        return response

    def test_expired_login_stops_worker_without_retry(self):
        replies = [self.response('{"msg":"未登录不能选课","loginUserId":""}'),
                   self.response(status=401), self.response('{"code":0,"message":"请重新登录"}')]
        redirect = self.response(status=302)
        redirect.url = "https://xk.bit.edu.cn/info"
        redirect.headers["Location"] = "https://sso.bit.edu.cn/cas/login?service=example"
        replies.append(redirect)
        login_page = self.response('<html><form>Login</form></html>')
        login_page.url = "https://sso.bit.edu.cn/cas/login"
        replies.append(login_page)
        empty_user = self.response('{"loginUserId":""}')
        empty_user.url = app.infoPage
        replies.append(empty_user)
        for response in replies:
            with self.subTest(status=response.status_code, url=response.url):
                app.stop_event.clear()
                app.login_expired.clear()
                with patch.object(requests.Session, "request", return_value=response) as request, \
                        patch.object(app.stop_event, "wait") as wait:
                    app.chooseCourse(self.course)
                self.assertTrue(app.stop_event.is_set())
                self.assertTrue(app.login_expired.is_set())
                self.assertEqual(request.call_count, 1)
                wait.assert_not_called()
                self.assertEqual(app.status["test"]["state"], "Login expired")

    def test_html_login_response_stops_worker_without_retry(self):
        response = self.response("<html><title>CAS Login</title><form action='/cas/login'>login</form></html>")
        response.url = "https://xk.bit.edu.cn/yjsxkapp/sys/xsxkappbit/xsxkCourse/choiceCourse.do"
        with patch.object(requests.Session, "request", return_value=response) as request:
            app.chooseCourse(self.course)
        self.assertEqual(request.call_count, 1)
        self.assertTrue(app.login_expired.is_set())
        self.assertTrue(app.stop_event.is_set())
        self.assertEqual(app.status["test"]["state"], "Login expired")

    def simulate_worker(self, replies, wait_step=None):
        clock = [0.0]
        waits = []
        items = iter(replies)

        def request(*args, **kwargs):
            result = next(items)
            if isinstance(result, Exception):
                raise result
            return result

        def wait(delay):
            waits.append(delay)
            clock[0] += delay if wait_step is None else wait_step
            if len(waits) >= len(replies):
                app.stop_event.set()

        with (patch.object(requests.Session, "request", side_effect=request) as mocked,
              patch.object(app.time, "monotonic", side_effect=lambda: clock[0]),
              patch.object(app.stop_event, "wait", side_effect=wait)):
            app.chooseCourse(self.course)
        return mocked.call_count, waits

    def test_many_full_course_responses_do_not_stop(self):
        count, waits = self.simulate_worker([self.response('{"code":0,"msg":"课程人数已满"}') for _ in range(20)])
        self.assertEqual(count, 20)
        self.assertEqual(waits, [0.01] * 20)
        self.assertEqual(app.status["test"]["fail"], 20)
        self.assertEqual(app.status["test"].get("errors", 0), 0)
        self.assertIsNone(app.stop_reason)

    def test_more_than_five_transient_failures_recover(self):
        for failure in [requests.ReadTimeout(), requests.ConnectionError(), self.response(status=503),
                        self.response(status=403), self.response('<html>maintenance 登录帮助</html>')]:
            with self.subTest(failure=repr(failure)):
                app.stop_event.clear()
                app.status["test"] = {"bjmc": "test", "success": 0, "fail": 0}
                count, _ = self.simulate_worker([failure] * 6 + [self.response()])
                self.assertEqual(count, 7)
                self.assertEqual(app.status["test"]["errors"], 6)
                self.assertEqual(app.status["test"]["fail"], 1)
                self.assertIsNone(app.stop_reason)
                self.assertFalse(app.login_expired.is_set())

    def test_continuous_outage_stops_only_failed_course(self):
        count, _ = self.simulate_worker([requests.ConnectionError()] * 30)
        self.assertLess(count, 30)
        self.assertFalse(app.stop_event.is_set())
        self.assertEqual(app.status["test"]["state"], "Unavailable")
        self.assertEqual(app.status["test"]["fail"], 0)

    def test_valid_response_resets_outage_duration(self):
        count, _ = self.simulate_worker([requests.ConnectionError()] * 2 + [self.response()] +
                                       [requests.ConnectionError()] * 2 + [self.response()], wait_step=100)
        self.assertEqual(count, 6)
        self.assertIsNone(app.stop_reason)
        self.assertEqual(app.status["test"]["fail"], 2)

    def test_rate_limit_obeys_retry_after(self):
        for value, expected in [('90', 90), (formatdate(1120, usegmt=True), 120), ('invalid', 2)]:
            with self.subTest(value=value):
                app.stop_event.clear()
                response = self.response(status=429)
                response.headers['Retry-After'] = value
                with patch.object(app.time, 'time', return_value=1000):
                    count, waits = self.simulate_worker([response, self.response()])
                self.assertEqual(count, 2)
                self.assertEqual(waits[0], expected)
                self.assertIsNone(app.stop_reason)

    def test_long_retry_after_exits_without_early_retry(self):
        response = self.response(status=429)
        response.headers['Retry-After'] = '600'
        count, waits = self.simulate_worker([response, self.response()])
        self.assertEqual(count, 1)
        self.assertEqual(waits, [300])
        self.assertEqual(app.status['test']['state'], 'Unavailable')

    def test_network_failure_stops_main_loop(self):
        def request(method, *args, **kwargs):
            if method == "GET":
                return self.response('{"csrfToken":"valid"}')
            raise requests.ConnectionError("offline")

        with patch.object(app, "courseList", [self.course]), \
                patch.object(app, "UNAVAILABLE_TIMEOUT", 0), \
                patch.object(requests.Session, "request", side_effect=request), \
                patch.object(app.stop_event, "wait", return_value=False), \
                patch.object(app.time, "sleep", return_value=None), \
                patch.object(app, "Live"):
            app.start()
        self.assertEqual(app.stop_reason, "All course workers unavailable")
        self.assertTrue(app.stop_event.is_set())

    def test_failed_course_does_not_stop_healthy_course(self):
        healthy = dict(self.course, bjdm="healthy")
        app.status["healthy"] = {"bjmc": "healthy", "success": 0, "fail": 0}

        def request(method, *args, **kwargs):
            if method == "GET":
                return self.response('{"csrfToken":"valid"}')
            if kwargs['data']['bjdm'] == 'test':
                raise requests.ConnectionError('offline')
            if app.status['test'].get('state') == 'Unavailable':
                app.stop_event.set()
            return self.response()

        with (patch.object(app, 'courseList', [self.course, healthy]),
              patch.object(app, 'UNAVAILABLE_TIMEOUT', 0),
              patch.object(requests.Session, 'request', side_effect=request),
              patch.object(app, 'Live')):
            app.start()
        self.assertEqual(app.status['test']['state'], 'Unavailable')
        self.assertGreater(app.status['healthy']['fail'], 0)
        self.assertIsNone(app.stop_reason)

    def test_html_mentioning_login_is_not_auth_failure(self):
        app.check_login(self.response('<html>服务暂不可用，请稍后登录</html>', 503))
        self.assertFalse(app.login_expired.is_set())

    def test_token_refresh_failures_stop_main_loop(self):
        with (
                patch.object(app, "courseList", [self.course]),
                patch.object(app, "chooseCourse", side_effect=lambda course: app.stop_event.wait()),
                patch.object(app, "UNAVAILABLE_TIMEOUT", 0),
                patch.object(requests.Session, "request", side_effect=requests.ConnectionError("offline")),
                patch.object(app.time, "sleep", return_value=None),
                patch.object(app, "Live"),
        ):
            app.start()
        self.assertEqual(app.stop_reason, "Token refresh unavailable")
        self.assertTrue(app.stop_event.is_set())

    def test_full_course_and_forbidden_are_not_login_expiry(self):
        for response in [self.response('{"code":0,"msg":"课程人数已满"}'), self.response(status=403)]:
            with patch.object(requests.Session, "request", return_value=response):
                try:
                    app.request_data("POST", "https://example.invalid/choice")
                except requests.HTTPError:
                    self.assertEqual(response.status_code, 403)
            self.assertFalse(app.stop_event.is_set())
            self.assertFalse(app.login_expired.is_set())

    def test_token_expiry_stops_other_workers(self):
        with patch.object(app, "courseList", [self.course]), \
                patch.object(app, "chooseCourse", side_effect=lambda course: app.stop_event.wait()), \
                patch.object(requests.Session, "request", return_value=self.response('{"msg":"未登录不能选课"}')) as request, \
                patch.object(app, "Live"):
            app.start()
        self.assertTrue(app.stop_event.is_set())
        self.assertEqual(request.call_count, 1)
        self.assertEqual(app.status["test"]["state"], "Login expired")

    def test_worker_recovers_from_bad_response(self):
        failures = [requests.ConnectionError("reset"), requests.ReadTimeout("slow"),
                    self.response("<html>login</html>"), self.response("{}"),
                    self.response("[]"), self.response(status=503)]
        for failure in failures:
            with self.subTest(failure=repr(failure)):
                app.stop_event.clear()
                app.status["test"]["fail"] = 0
                app.status["test"]["errors"] = 0
                calls = []

                def request(*args, **kwargs):
                    calls.append(kwargs)
                    if len(calls) == 1:
                        if isinstance(failure, Exception):
                            raise failure
                        return failure
                    app.stop_event.set()
                    return self.response()

                with patch.object(requests.Session, "request", side_effect=request), \
                        patch.object(app.stop_event, "wait", return_value=False):
                    app.chooseCourse(self.course)
                self.assertEqual(len(calls), 2)
                self.assertEqual(app.status["test"]["fail"], 1)
                self.assertEqual(app.status["test"]["errors"], 1)

    def test_requests_have_timeout_and_ignore_system_proxy(self):
        captured = []

        def send(request, **kwargs):
            captured.append(kwargs)
            return self.response()

        with patch.dict("os.environ", {"HTTPS_PROXY": "http://127.0.0.1:9"}), \
                patch("requests.sessions.get_environ_proxies", return_value={"https": "http://127.0.0.1:9"}), \
                patch.object(requests.adapters.HTTPAdapter, "send", side_effect=send):
            self.assertIsNotNone(app.postData("https://example.invalid/courses", {}))
        self.assertIsNotNone(captured[0]["timeout"])
        self.assertFalse(captured[0]["proxies"])

    def test_proxy_opt_in(self):
        with patch.object(app, "use_system_proxy", True), \
                patch("requests.sessions.get_environ_proxies", return_value={"https": "http://127.0.0.1:9"}), \
                patch.object(requests.adapters.HTTPAdapter, "send", return_value=self.response()) as send:
            app.postData("https://example.invalid/courses", {})
        self.assertEqual(send.call_args.kwargs["proxies"]["https"], "http://127.0.0.1:9")

    def test_success_is_counted(self):
        def request(*args, **kwargs):
            app.stop_event.set()
            return self.response('{"code": 1}')

        with patch.object(requests.Session, "request", side_effect=request):
            app.chooseCourse(self.course)
        self.assertEqual(app.status["test"]["success"], 1)
        self.assertEqual(app.status["test"]["fail"], 0)

    def test_workers_reuse_separate_sessions_and_close_them(self):
        barrier = threading.Barrier(2)
        local = threading.local()
        sessions = {"test": [], "other": []}
        closed = []
        other = dict(self.course, bjdm="other")
        app.status["other"] = {"bjmc": "other", "success": 0, "fail": 0}

        def request(session, *args, **kwargs):
            local.calls = getattr(local, "calls", 0) + 1
            sessions[kwargs["data"]["bjdm"]].append(session)
            if local.calls == 1:
                barrier.wait(timeout=5)
            return self.response()

        with patch.object(requests.Session, "request", autospec=True, side_effect=request), \
                patch.object(requests.Session, "close", autospec=True, side_effect=closed.append), \
                patch.object(app.stop_event, "is_set", side_effect=lambda: getattr(local, "calls", 0) >= 3), \
                patch.object(app.stop_event, "wait", return_value=False), \
                ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(app.chooseCourse, course) for course in (self.course, other)]
            for future in futures:
                future.result(timeout=10)
        for calls in sessions.values():
            self.assertEqual(len(calls), 3)
            self.assertTrue(all(session is calls[0] for session in calls))
            self.assertEqual(closed.count(calls[0]), 1)
        self.assertIsNot(sessions["test"][0], sessions["other"][0])

    def test_worker_reuses_actual_http_connection(self):
        clients = []

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                clients.append(self.client_address)
                if len(clients) == 3:
                    app.stop_event.set()
                body = b'{"code": 0}'
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with patch.object(app, "sourceUrl", f"http://127.0.0.1:{server.server_port}/?_="):
                    app.chooseCourse(self.course)
            finally:
                server.shutdown()
                thread.join(timeout=5)
        self.assertEqual(len(clients), 3)
        self.assertEqual(len(set(clients)), 1)

    def test_http_failure_recovery_then_login_expiry(self):
        received = []
        replies = [(503, b'busy'), (429, b'limited'), (200, b'{"code":0}'),
                   (200, '{"msg":"未登录不能选课"}'.encode())]

        class Handler(BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'

            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                code, body = replies[min(len(received), 3)]
                received.append(code)
                self.send_response(code)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                if code == 429:
                    self.send_header('Retry-After', '60')
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        with ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with (patch.object(app, 'sourceUrl', f'http://127.0.0.1:{server.server_port}/?_='),
                      patch.object(app.stop_event, 'wait', return_value=False) as wait):
                    app.chooseCourse(self.course)
            finally:
                server.shutdown()
                thread.join(timeout=5)
        self.assertEqual(received, [503, 429, 200, 200])
        self.assertEqual([call.args[0] for call in wait.call_args_list], [2, 60, 0.01])
        self.assertEqual(app.status['test']['fail'], 1)
        self.assertEqual(app.status['test']['errors'], 2)
        self.assertEqual(app.stop_reason, 'Login expired')
        self.assertTrue(app.stop_event.is_set())

    def test_heartbeat_and_shutdown(self):
        with patch.object(app, "courseList", [self.course]), \
                patch.object(app, "chooseCourse", side_effect=lambda course: app.stop_event.wait()), \
                patch.object(requests.adapters.HTTPAdapter, "send", return_value=self.response('{"csrfToken": "new"}')) as send, \
                patch.object(app, "Live"), \
                patch.object(app.time, "sleep", side_effect=KeyboardInterrupt):
            app.start()
        self.assertEqual(self.course["csrfToken"], "new")
        self.assertIsNotNone(send.call_args.kwargs["timeout"])
        self.assertFalse(send.call_args.kwargs["proxies"])
        self.assertTrue(app.stop_event.is_set())


if __name__ == "__main__":
    unittest.main()
