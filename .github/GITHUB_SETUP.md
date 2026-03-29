# GitHub 儲存庫設定（Description、Topics、Releases、Packages、Tags）

以下需在 [github.com/dragonheart8787/rocket_program](https://github.com/dragonheart8787/rocket_program) 網頁上手動操作（無法只靠 Git 推送完成）。

## Repository description（簡短說明）

建議貼上（英文，搜尋友善）：

```text
Python rocket design toolkit: mission ΔV, propulsion, structures, thermal, GNC, V&V, UQ, benchmarks, aero surrogates. MIT.
```

或中文版：

```text
Python 火箭設計工具：任務 ΔV、推進、結構、熱力、GNC、V&V、不確定度、對標與氣動代理。MIT 授權。
```

設定位置：**倉庫首頁 → About 右側齒輪 → Description**。

## Topics（核心關鍵字標籤）

建議新增 Topics（可搜尋、利於探索）：

`rocket` `aerospace` `propulsion` `launch-vehicle` `trajectory` `GNC` `systems-engineering` `python` `numpy` `verification-validation` `uncertainty-quantification` `aerodynamics` `rocket-science` `engineering-simulation` `LEO`

設定位置：**About → ⚙️ → Topics**。

## Tags（版本標籤）

在本地建立並推送標籤（與 [CHANGELOG.md](../CHANGELOG.md) 版本一致）：

```bash
git tag -a v1.0.0 -m "Release v1.0.0: packaged layout, README, MIT license"
git push origin v1.0.0
```

## Releases（發行說明）

1. 推送 `v1.0.0` 等 **tag** 後，到 **Releases → Draft a new release**。
2. **Choose a tag** 選 `v1.0.0`。
3. **Release title**：例如 `v1.0.0`。
4. **Describe release**：可複製 `CHANGELOG.md` 中該版本段落，或簡述「套件化目錄、README、授權」。
5. 可附加 **Source code (zip/tar)**（GitHub 會自動產生）。

可選：在 **Actions** 啟用 `.github/workflows/release.yml` 後，推送 tag 會自動建立 Release 草稿／紀錄（依 workflow 內容而定）。

## Packages（套件／容器）

- **Python（PyPI）**：本專案已提供 `pyproject.toml`。若要發佈到 PyPI，需帳號與 API token，於 CI 使用 `twine upload`（勿將 token 寫入程式碼）。
- **GitHub Packages**：可發佈 Docker 映像或 Maven/npm 等；本專案為純 Python 函式庫時，多數使用者以 `pip install git+https://github.com/dragonheart8787/rocket_program.git` 或本地 `pip install -e .` 即可。

建議在 README 註明安裝方式即可，不必強制開 GitHub Packages。
