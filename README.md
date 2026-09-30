# 삼보사진관 (SAMBO PHOTO STUDIO)

**사진은 그대로, 규격은 정확하게.**

Windows PC에서 여러 장의 사진을 불러와 비율, 픽셀 크기, 증명사진형, 인화형, 액자형 규격으로 재단·리사이즈하고 일괄 저장하는 데스크톱 도구입니다.

## V0.1 기능

- 여러 장 사진 추가 및 폴더 일괄 추가
- Drag & Drop
- 사진별 개별 출력 설정
- 현재 설정을 모든 사진에 일괄 적용
- 비율 프리셋: 1:1, 3:4, 4:3, 4:5, 5:4, 2:3, 3:2, 9:16, 16:9
- 증명/여권형 크기 프리셋
- 인화/액자 프리셋
- px / mm / cm / inch
- DPI 기반 실제 픽셀 자동 계산
- 꽉 채우기 / 전체 유지 / 직접 재단
- 직접 재단 시 확대 + 좌우/상하 위치 조정
- 90° 회전
- JPEG / PNG / WebP 저장
- 개별 저장 / 전체 저장
- EXIF 방향 자동 보정
- 원본 파일 비파괴

> 증명/여권형 프리셋은 **사진 크기 편집용**입니다. 국가/기관별 최신 얼굴 위치·배경·촬영일 등 제출 요건의 적합성을 보증하지 않습니다.

## 개발 실행

Windows PowerShell 또는 CMD에서:

```bat
run_dev.bat
```

또는 직접:

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
python main.py
```

## 로컬 Windows EXE 빌드

```bat
build_windows.bat
```

성공하면:

```text
dist/삼보사진관.exe
```

## GitHub 연결

이 폴더 자체가 GitHub repository root입니다.

```bash
git init
git add .
git commit -m "Initial Sambo Photo Studio V0.1"
git branch -M main
git remote add origin https://github.com/<YOUR_ID>/sambo-photo-studio.git
git push -u origin main
```

Push하면 `.github/workflows/windows-build.yml`이 실행되어 Windows EXE를 Actions Artifact로 생성합니다.

### Release 만들기

```bash
git tag v0.1.0
git push origin v0.1.0
```

`v*` 태그가 push되면 `release-windows.yml`이 `삼보사진관.exe`를 빌드하고 GitHub Release에 첨부합니다.

## 프로젝트 구조

```text
sambo-photo-studio/
├─ main.py
├─ sambo_photo/
│  ├─ models.py
│  ├─ presets.py
│  ├─ image_engine.py
│  └─ main_window.py
├─ presets/
├─ tests/
├─ .github/workflows/
├─ pyproject.toml
├─ sambo_photo_studio.spec
├─ build_windows.bat
└─ run_dev.bat
```

## V0.2 후보

- 얼굴 자동 감지 + 증명사진 가이드
- 마우스 직접 드래그 Crop
- 사진별 작업 상태 저장/불러오기
- EXIF/ICC profile 보존 강화
- 동일 사진 여러 규격 동시 출력
- 인쇄용 시트 배치
