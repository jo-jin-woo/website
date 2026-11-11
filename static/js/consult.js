(function () {
  var form = document.querySelector('.consult-form');
  if (!form) return;
  var sido = form.sido, sgg = form.sigungu, msg = form.querySelector('.form-msg');
  var areas = window.AREA_OPTIONS || {};
  Object.keys(areas).forEach(function (k) { sido.add(new Option(k, k)); });
  sido.addEventListener('change', function () {
    sgg.length = 1;
    (areas[sido.value] || []).forEach(function (v) { sgg.add(new Option(v, v)); });
    sgg.disabled = !sido.value;
  });
  form.page.value = location.pathname;
  form.page_title.value = document.title;

  // 메뉴 토글 (모바일)
  var tg = document.querySelector('.nav-toggle');
  if (tg) tg.addEventListener('click', function () {
    document.body.classList.toggle('nav-open');
    tg.setAttribute('aria-expanded', document.body.classList.contains('nav-open'));
  });

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var err = '';
    if (!form.name.value.trim()) err = '이름을 입력해 주세요.';
    else if (!/^[0-9\-+ ]{9,20}$/.test(form.phone.value.trim())) err = '연락처를 정확히 입력해 주세요.';
    else if (!form.message.value.trim()) err = '문의사항을 입력해 주세요.';
    else if (!form.agree.checked) err = '개인정보 수집 및 이용에 동의해 주세요.';
    if (err) { msg.textContent = err; msg.className = 'form-msg error'; return; }
    var btn = form.querySelector('button[type=submit]');
    btn.disabled = true; msg.textContent = '전송 중입니다…'; msg.className = 'form-msg';
    fetch(form.action, { method: 'POST', body: new URLSearchParams(new FormData(form)), headers: { 'Accept': 'application/json' } })
      .then(function (r) { return r.json().catch(function () { return { ok: false, message: '서버 응답 오류' }; }); })
      .then(function (d) {
        msg.textContent = d.message || (d.ok ? '접수되었습니다.' : '전송에 실패했습니다.');
        msg.className = 'form-msg ' + (d.ok ? 'ok' : 'error');
        if (d.ok) { form.reset(); sgg.length = 1; sgg.disabled = true; }
      })
      .catch(function () {
        msg.textContent = '전송에 실패했습니다. 전화로 문의해 주세요.'; msg.className = 'form-msg error';
      })
      .then(function () { btn.disabled = false; });
  });
})();
