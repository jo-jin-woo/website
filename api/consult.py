"""
Vercel 서버리스 함수: /api/consult
상담 폼 전체 내용을 이메일로 발송.
메일 설정은 Vercel 프로젝트 → Settings → Environment Variables 에 입력 (GitHub 에는 올라가지 않음)
  NOTIFY_EMAIL, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SITE_NAME
"""
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
import os, json, re, ssl, smtplib, html, datetime

KST = datetime.timezone(datetime.timedelta(hours=9))

def collect(f, ip, ua):
    g = lambda k, n: str(f.get(k, "")).replace("\r", "").strip()[:n]
    return {
        "이름": g("name", 30), "연락처": g("phone", 20), "시/도": g("sido", 20), "시/군/구": g("sigungu", 20),
        "상세주소": g("address", 120), "문의 유형": g("topic", 30), "문의사항": g("message", 2000),
        "개인정보 동의": "동의" if f.get("agree") else "미동의",
        "신청 페이지": f'{g("page_title", 150)} ({g("page", 200)})',
        "접수 시각": datetime.datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S"),
        "IP": ip, "브라우저": ua[:200],
    }

def validate(d):
    if not d["이름"]: return "이름을 입력해 주세요."
    if not re.fullmatch(r"[0-9\-+ ]{9,20}", d["연락처"]): return "연락처를 정확히 입력해 주세요."
    if not d["문의사항"]: return "문의사항을 입력해 주세요."
    if d["개인정보 동의"] != "동의": return "개인정보 수집 및 이용에 동의해 주세요."
    return ""

def send(d, env):
    site, to = env.get("SITE_NAME", "상담"), env["NOTIFY_EMAIL"]
    subject = f"[{site} 상담신청] {d['이름']} / {(d['시/도'] + ' ' + d['시/군/구']).strip()} / {d['연락처']}"
    text = "새 상담 신청이 접수되었습니다.\n\n" + "".join(f"■ {k}: {v}\n" for k, v in d.items())
    rows = "".join(
        f'<tr><th style="text-align:left;padding:8px 12px;background:#f3f6fb;border:1px solid #dde3ec;white-space:nowrap;vertical-align:top">{html.escape(k)}</th>'
        f'<td style="padding:8px 12px;border:1px solid #dde3ec">{html.escape(v).replace(chr(10), "<br>")}</td></tr>' for k, v in d.items())
    tel = re.sub(r"[^0-9+]", "", d["연락처"])
    body = (f'<div style="font-family:맑은 고딕,sans-serif;font-size:14px"><h2 style="color:#0b5ed7">새 상담 신청</h2>'
            f'<table style="border-collapse:collapse;width:100%;max-width:640px">{rows}</table>'
            f'<p style="margin-top:16px"><a href="tel:{tel}" style="background:#0b5ed7;color:#fff;padding:10px 16px;border-radius:6px;text-decoration:none">📞 {html.escape(d["연락처"])} 바로 전화</a></p></div>')
    msg = MIMEMultipart("alternative")
    msg["From"] = formataddr((str(Header(site, "utf-8")), env["SMTP_USER"]))
    msg["To"] = to
    msg["Subject"] = Header(subject, "utf-8")
    msg.attach(MIMEText(text, "plain", "utf-8")); msg.attach(MIMEText(body, "html", "utf-8"))
    port = int(env.get("SMTP_PORT") or 465)
    ctx = ssl.create_default_context()
    s = smtplib.SMTP_SSL(env["SMTP_HOST"], port, context=ctx, timeout=15) if port == 465 else smtplib.SMTP(env["SMTP_HOST"], port, timeout=15)
    with s:
        if port != 465: s.starttls(context=ctx)
        s.login(env["SMTP_USER"], env["SMTP_PASS"])
        s.sendmail(env["SMTP_USER"], [to], msg.as_string())

class handler(BaseHTTPRequestHandler):
    def _reply(self, ok, message, code=200):
        b = json.dumps({"ok": ok, "message": message}, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        self._reply(False, "잘못된 요청입니다.", 405)

    def do_POST(self):
        n = min(int(self.headers.get("Content-Length") or 0), 20000)
        raw = self.rfile.read(n).decode("utf-8", "replace")
        f = {k: v[0] for k, v in parse_qs(raw).items()}
        if f.get("website"): return self._reply(True, "접수되었습니다.")       # 스팸봇
        ip = (self.headers.get("x-forwarded-for") or "").split(",")[0].strip()
        d = collect(f, ip, self.headers.get("User-Agent", ""))
        err = validate(d)
        if err: return self._reply(False, err, 400)
        env = os.environ
        if not all(env.get(k) for k in ("NOTIFY_EMAIL", "SMTP_HOST", "SMTP_USER", "SMTP_PASS")):
            return self._reply(False, "상담 접수 설정이 완료되지 않았습니다. 전화로 문의해 주세요.", 500)
        try:
            send(d, env)
        except Exception as e:
            print("mail error:", e)
            return self._reply(False, "일시적인 오류로 접수하지 못했습니다. 전화로 문의해 주세요.", 500)
        self._reply(True, "상담 신청이 접수되었습니다. 확인 후 연락드리겠습니다.")
