import unittest
import threading
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

import requests

import CourseRace as app


class CourseRaceTests(unittest.TestCase):
    def setUp(self):
        app.stop_event.clear()
        app.login_expired.clear()
        self.course = {"bjdm": "test", "lx": "0", "csrfToken": ""}
        app.status["test"] = {"bjmc": "test", "success": 0, "fail": 0}

    def tearDown(self):
        app.stop_event.clear()
        app.login_expired.clear()
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
                self.assertEqual(app.status["test"]["fail"], 2)

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
