# 삼보사진관 (SAMBO PHOTO STUDIO)

**사진은 그대로, 규격은 정확하게.**

Windows PC에서 사진 규격 변환·재단·비파괴 누끼를 처리하는 데스크톱 도구입니다.

## V0.2 — 비파괴 누끼 / 배경

- 자동 누끼는 원본 픽셀을 수정하지 않고 별도 PNG 마스크 초안만 생성
- 원본 / 결과 / 마스크 보기
- 복구 브러시와 제거 브러시
- 투명 배경 PNG / 사용자 지정 색상 배경
- 마스크 휴리스틱 검사로 이상 결과는 ‘검토 필요’ 표시
- 가짜 퍼센트형 AI 신뢰도는 표시하지 않음
- 자동/수정 누끼는 ‘누끼 확정’ 전 배경 제거 결과 저장 차단
- 회전 시 기존 마스크를 안전하게 폐기
- 첫 자동 누끼 실행 시 소형 모델 다운로드 가능, 이후 로컬 캐시 재사용

> 핵심 원칙: 잘 따는 것보다 잘못 따도 원본을 절대 훼손하지 않는 것을 우선합니다.

## 기본 기능

- 다중 사진/폴더 추가 및 Drag & Drop
- 사진별 설정 / 전체 일괄 적용
- 1:1, 3:4, 4:3, 4:5, 5:4, 2:3, 3:2, 9:16, 16:9
- 증명/여권형, 인화, 액자 프리셋
- px / mm / cm / inch + DPI 자동계산
- 꽉 채우기 / 전체 유지 / 직접 재단
- 확대 / 좌우·상하 이동 / 90° 회전
- JPEG / PNG / WebP
- 원본 비파괴

## 개발 실행

~~~bat
run_dev.bat
~~~

## Windows EXE 빌드

~~~bat
build_windows.bat
~~~

성공하면 dist/삼보사진관.exe 가 생성됩니다.

## GitHub Actions

main push 또는 Pull Request에서 Windows Build workflow가 테스트와 EXE 빌드를 수행합니다.

## 주요 구조

~~~text
sambo-photo-studio/
├─ main.py
├─ sambo_photo/
│  ├─ models.py
│  ├─ presets.py
│  ├─ image_engine.py
│  ├─ background_engine.py
│  ├─ mask_editor.py
│  └─ main_window.py
├─ presets/
├─ tests/
└─ .github/workflows/
~~~

## 다음 후보

- 인물/일반 목적물별 누끼 모델 선택
- 머리카락·반투명 경계 refinement
- 직접 드래그 Crop
- 얼굴 자동 감지 + 증명사진 가이드
- 프로젝트 저장/불러오기
- 동일 원본 여러 규격 동시 출력
