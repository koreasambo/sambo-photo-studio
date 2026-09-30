# GitHub 연동 순서

## 1. 새 저장소 만들기

권장 저장소 이름: `sambo-photo-studio`

초기에는 **Private repository**를 권장합니다. 별도 LICENSE를 아직 선택하지 않았으므로 공개 저장소로 배포하기 전 라이선스를 결정하세요.

## 2. 로컬 폴더에서 최초 Push

```bash
git init
git add .
git commit -m "Initial Sambo Photo Studio V0.1"
git branch -M main
git remote add origin https://github.com/<YOUR_ID>/sambo-photo-studio.git
git push -u origin main
```

## 3. GitHub Actions 확인

Repository → Actions → `Windows Build`

`main` push마다 테스트 후 `삼보사진관.exe`를 빌드합니다.

빌드가 끝나면 실행 화면 하단의 Artifacts에서 `sambo-photo-studio-windows`를 내려받습니다.

## 4. 정식 버전 배포

```bash
git tag v0.1.0
git push origin v0.1.0
```

태그가 올라가면 `Windows Release` workflow가 실행되고 GitHub Release에 `삼보사진관.exe`가 첨부됩니다.

## 5. 다음 개발 방식

- `main`: 실행 가능한 안정본
- 기능 개발: `feature/<기능명>` branch
- 수정 후 Pull Request → Windows Build 통과 → main merge
