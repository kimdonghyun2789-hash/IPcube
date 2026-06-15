"""IP3 API 진단 스크립트 (로컬 실행용).

이 클라우드 세션에서는 외부 인터넷이 차단되어 API 테스트를 할 수 없습니다.
네트워크가 정상인 본인 PC에서 아래처럼 실행하세요.

    python check_api.py

키는 .env 또는 앱 설정(data/ip3.db)에서 자동으로 읽습니다.
직접 넘길 수도 있습니다:

    python check_api.py --kipris 키값 --gemini 키값

KIPRISPlus는 계정에 따라 키 파라미터명/서비스 경로가 다를 수 있어,
여러 조합을 자동으로 시도하고 어떤 조합이 동작하는지 표시합니다.
출력 결과를 그대로 복사해 알려주시면 설정을 정확히 맞춰드립니다.
"""
from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

try:
    from utils import config
except Exception:  # 단독 실행 대비
    config = None

KIPRIS_BASES = [
    "http://plus.kipris.or.kr/kipo-api/kipi",
    "http://plus.kipris.or.kr/openapi/rest",
]
# 서비스경로 / 키파라미터명 / 페이지 파라미터 조합 후보
KIPRIS_SERVICES = [
    "patUtiModInfoSearchSevice",
    "patUtiModInfoSearchService",
    "patUtiliInfoSearchSevice",
    "patUtilityInfoSearchService",
]
KIPRIS_KEY_PARAMS = ["ServiceKey", "accessKey"]
KIPRIS_PAGE_PROFILES = [
    ("docs", {"word": "전기", "docsStart": 1, "docsCount": 3}),
    ("rows", {"word": "전기", "numOfRows": 3, "pageNo": 1}),
]


def _mask(key: str) -> str:
    if not key:
        return "(없음)"
    return key[:4] + "…" + key[-4:] if len(key) > 8 else "****"


def _local(tag: str) -> str:
    return tag.split("}")[-1]


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def check_kipris(key: str) -> None:
    print("\n" + "=" * 60)
    print(f"[KIPRISPlus] 키: {_mask(key)}")
    print("=" * 60)
    if not key:
        print("  키가 없습니다. --kipris 로 넘기거나 설정에 저장하세요.")
        return

    found = False
    for base_url in KIPRIS_BASES:
        for service in KIPRIS_SERVICES:
            for key_param in KIPRIS_KEY_PARAMS:
                for page_mode, base_params in KIPRIS_PAGE_PROFILES:
                    url = f"{base_url}/{service}/getWordSearch"
                    params = {**base_params, key_param: key}
                    label = (
                        f"  {base_url}/{service}/getWordSearch "
                        f"(key={key_param}, page={page_mode})"
                    )
                    try:
                        req_url = url + "?" + urllib.parse.urlencode(params)
                        req = urllib.request.Request(req_url, method="GET")
                        opener = urllib.request.build_opener(NoRedirectHandler)
                        with opener.open(req, timeout=20) as resp:
                            status = resp.status
                            headers = dict(resp.headers)
                            content = resp.read()
                    except urllib.error.HTTPError as exc:
                        status = exc.code
                        headers = dict(exc.headers)
                        content = exc.read()
                    except Exception as exc:
                        print(
                            f"{label}\n      -> 네트워크 오류: {exc.__class__.__name__}"
                        )
                        continue
                    snippet = content[:160].decode("utf-8", "replace").replace("\n", " ").strip()
                    if not snippet and headers.get("Location"):
                        snippet = f"Location: {headers['Location']}"
                    try:
                        root = ET.fromstring(content)
                        items = [e for e in root.iter() if _local(e.tag) == "item"]
                        codes = [
                            e.text.strip()
                            for e in root.iter()
                            if _local(e.tag) in ("resultCode", "successYN") and e.text
                        ]
                        msgs = [
                            e.text.strip()
                            for e in root.iter()
                            if _local(e.tag) in ("resultMsg", "message") and e.text
                        ]
                        status_text = f"HTTP {status} · XML OK · item {len(items)}개"
                        if codes:
                            status_text += f" · code={codes[0]}"
                        if msgs:
                            status_text += f" · msg={msgs[0]}"
                        print(f"{label}\n      -> {status_text}")
                        if items:
                            title = next(
                                (
                                    e.text
                                    for e in items[0].iter()
                                    if _local(e.tag)
                                    in ("inventionName", "inventionTitle")
                                    and e.text
                                ),
                                "",
                            )
                            print(f"         예시 특허명: {title}")
                            print(
                                "      동작하는 조합입니다. 설정값: "
                                f"kipris_base_url={base_url}, "
                                f"kipris_service={service}, "
                                f"kipris_key_param={key_param}, "
                                f"kipris_page_mode={page_mode}"
                            )
                            found = True
                            break
                    except ET.ParseError:
                        print(
                            f"{label}\n      -> HTTP {status} · XML 아님 · 응답: {snippet}"
                        )
                if found:
                    break
            if found:
                break
        if found:
            break

    if not found:
        print("\n  ⚠️  동작하는 조합을 찾지 못했습니다. 위 응답 내용을 복사해 알려주세요.")


def check_gemini(key: str) -> None:
    print("\n" + "=" * 60)
    print(f"[Gemini] 키: {_mask(key)}")
    print("=" * 60)
    if not key:
        print("  키가 없습니다. --gemini 로 넘기거나 설정에 저장하세요.")
        return
    try:
        from google import genai as google_genai

        client = google_genai.Client(api_key=key)
        target = "gemini-3.5-flash"
        print(f"\n  '{target}' 모델로 생성 테스트…")
        resp = client.models.generate_content(
            model=target, contents="한 단어로 'OK' 라고만 답하세요."
        )
        print(f"  ✅ 응답: {getattr(resp, 'text', '')!r}")
        return
    except ImportError:
        pass
    except Exception as exc:
        print(f"  google-genai 생성 실패: {exc}")
        return

    try:
        import google.generativeai as genai
    except ImportError:
        print("  google-genai/google-generativeai 미설치. 설치: pip install google-genai")
        return

    genai.configure(api_key=key)
    try:
        models = [
            m.name.split("/")[-1]
            for m in genai.list_models()
            if "generateContent" in (getattr(m, "supported_generation_methods", []) or [])
        ]
    except Exception as exc:
        print(f"  모델 목록 조회 실패: {exc}")
        print("  -> 키가 유효하지 않거나 권한이 없을 수 있습니다.")
        return

    print(f"  generateContent 지원 모델 {len(models)}개:")
    for m in models[:20]:
        print(f"    - {m}")

    candidates = ["gemini-2.0-flash", "gemini-flash-latest", "gemini-2.5-flash"]
    target = next((c for c in candidates if c in models), None)
    if not target:
        target = next((m for m in models if "flash" in m), models[0] if models else None)
    if not target:
        print("  사용 가능한 모델이 없습니다.")
        return
    print(f"\n  '{target}' 모델로 생성 테스트…")
    try:
        model = genai.GenerativeModel(target)
        resp = model.generate_content("한 단어로 'OK' 라고만 답하세요.")
        print(f"  ✅ 응답: {getattr(resp, 'text', '')!r}")
        print(f"  -> 앱에서는 provider 기본 모델을 자동 사용합니다: {target}")
    except Exception as exc:
        print(f"  생성 실패: {exc}")


def main() -> None:
    ap = argparse.ArgumentParser(description="IP3 API 진단")
    ap.add_argument("--kipris", default="", help="KIPRISPlus API Key")
    ap.add_argument("--gemini", default="", help="Gemini API Key")
    args = ap.parse_args()

    kipris = args.kipris
    gemini = args.gemini
    if config is not None:
        kipris = kipris or config.get_kiprisplus_key()
        if not gemini and config.get_ai_provider() == "Gemini":
            gemini = config.get_ai_key()

    print("IP3 API 진단 시작 (이 출력 전체를 복사해 공유하면 정확히 도와드립니다)")
    check_kipris(kipris)
    check_gemini(gemini)
    print("\n진단 완료.")


if __name__ == "__main__":
    sys.exit(main())
