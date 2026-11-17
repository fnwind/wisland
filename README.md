# Wisland · Windows 液态灵动岛

贴在屏幕边缘的液态毛玻璃胶囊，悬停弹性展开。Windows 10 / 11，Python + PySide6。

<p align="center"><img src="docs/home.png" width="720"></p>

## 安装

1. 准备一个 Python 运行环境，二选一：
   - **uv**（推荐，几十 MB，装依赖也快）：`winget install astral-sh.uv`
     setup.bat 会直接用它建 `.venv`，没有 3.12 就自动下（不需要 `py` 启动器，也不需要 `python` 在 PATH 里）
   - **Python 3.10 或更新版本**：<https://www.python.org/downloads/windows/>
     （安装时勾选 **Add python.exe to PATH**）
2. 下载本项目：右侧 **Releases** 里下载 `wisland-x.y.z.zip` 并解压
   （或 `git clone https://github.com/AsamiAkito/wisland.git`）。
   路径里最好不要有特殊字符。
3. 双击 **`setup.bat`**：自动创建 `.venv`、补齐 pip、安装依赖（PyPI 连不上时自动改用清华镜像），需要几分钟。
4. 双击 **`wisland.vbs`** 启动。还没运行过 `setup.bat` 时，它会提示并帮你运行。

开机自启：右键灵动岛 → 开机自启。

## 功能

- **液态外形**：与屏幕边缘以表面张力相连；按住拖动会拉丝、断开，松手吸附到最近的边缘
- **收起态**：时间天气 / 小形象 / 正在播放，滚轮切换；开始播放音乐时自动显示**滚动歌词**（加宽显示完整一句，右侧可直接播放 / 暂停）；实时字幕时上日语、下中文两行显示；新消息、音量、股票提醒以动画浮现
- **小形象**：发光双眼，跟随鼠标，靠近时随机变换表情；按压会被挤歪
- **音乐**：网易云音乐（直接读取本地播放日志，无需插件）、QQ 音乐、Spotify、B 站 / 浏览器等；歌词来自网易云公开歌词（含翻译）
- **主页**：播放控制、展开方式、可穿透、静音、实时字幕、应用启动器
- **消息**：QQ / 微信 / 邮件 提醒（读取 Windows 通知与任务栏闪烁，不读消息内容）
- **股票**：A 股 / 港股 / 美股行情与分时（腾讯财经公开接口），点 + 搜索添加，右键删除
- **天气**：多城市，逐小时与 5 天预报（默认 Open-Meteo，无需 Key）
- **控制**：音量、亮度、WLAN、蓝牙（不读取 Wi-Fi 名称，因此不会触发 Windows 的位置访问）；检测到 Clash Verge 时显示代理控制
- **剪贴板**：最近 10 条文字 / 图片，点击复制
- **翻译**：日译中；实时字幕（系统声音 → 日语识别 → 翻译），滚轮上翻查看历史，点词查词，加入单词本并同步到 Anki
- **主题**：深色 / 浅色 / 胭脂撞色 / 晴空渐变

操作：悬停展开（停在上次看的页面），鼠标离开收起；**双击**灵动岛切换「长关」（不再自动展开）；右键打开菜单（主题、展开方式、**面板开关**、可穿透、编辑配置等）。

## 可选设置

配置文件是 `config.json`（首次启动自动生成；右键灵动岛 → 编辑配置，改完后右键 → 重新加载配置）。

| 功能 | 需要什么 |
| --- | --- |
| 翻译、实时字幕的中文翻译 | DeepSeek API Key → `translate.api_key` |
| 实时字幕的日语识别 | 无需设置：第一次点「开始聆听」会自动下载识别模型（约 630 MB，可断点续传，连不上 Hugging Face 时自动改用 hf-mirror 镜像） |
| 点词查词的词典 | `.venv\Scripts\python.exe scripts\download_models.py --dict` |
| 天气用 OpenWeather | `weather.api_key`（留空则使用 Open-Meteo） |
| 天气是否走代理 | `weather.proxy`：留空 = **直连**（默认，不会经过 Clash 等系统代理）；`"env"` = 跟随系统 / 环境变量代理；也可填 `http://127.0.0.1:7897` |
| 自选股 | 股票页点 **+** 搜索添加，或编辑 `stocks.watchlist` |
| 邮件未读提醒（不开 Thunderbird） | `mail.imap` 里填 IMAP 授权码 |
| 同步到 Anki | 安装 Anki 插件 AnkiConnect |
| 不要某个面板（如股票） | 直接在 **右键菜单 → 面板** 里点一下（立刻生效，不用重启）；也可以编辑 `pages.hidden`，key 为 `msg` / `stock` / `weather` / `ctl` / `clip` / `trans`（`home` 是导航锚点，不能隐藏） |

## 常见问题

- **setup.bat 报「Neither uv nor Python 3.10 or newer was found」**：`where uv` 要能查到 uv（uv 默认装在 `%USERPROFILE%\.local\bin`，重开一次终端 / 注销再登录让 PATH 生效）；
  conda 的 `python` 也认，但要保证它在 PATH 里且版本 ≥ 3.10；用 python.org 安装包装的 Python 则是漏勾了 **Add python.exe to PATH**，
  重新运行安装程序选 Modify 勾上即可。
- **双击 vbs 报错 80070002 / 没反应 / No module named 'PySide6'**：依赖没装进 `.venv`，运行 `setup.bat`（不要用全局的 `pip install`）；还不行就删掉 `.venv` 文件夹再运行一次。日志在 `data\wisland.log`。
- **实时字幕没反应**：第一次使用要先下载模型，按钮旁会显示下载进度；下载失败时检查网络 / 代理后再点一次，会接着下载。没有填 DeepSeek Key 时只显示日语、不翻译。
- **天气请求超时**：天气默认直连、不走系统代理（开着 Clash 也不影响）。如果直连反而不通，把 `weather.proxy` 改成 `"env"` 或你的代理地址（如 `http://127.0.0.1:7897`）。
- **哪些请求会走系统代理**：天气、股票、网易云歌词、DeepSeek 翻译与实时字幕都是**直连**（国内接口绕道代理只会更慢、更容易超时）；只有实时字幕的识别模型下载（HuggingFace / hf-mirror）会先试系统代理，不行再直连。
- **setup.bat 提示找不到 Python**：见上面第一条（uv 不在 PATH，或 python.org 装的时候没勾 Add to PATH）。
- **没显示正在播放 / 没有歌词**：网易云无需设置（读取它的本地日志）；QQ 音乐需在 设置 → 常规设置 中勾选「显示系统媒体传输控制(SMTC)」。没有接入系统媒体控件的播放器，播放按钮会改发键盘媒体键。周杰伦等网易云没有版权的歌曲没有歌词。
- **不想自动切到音乐 / 不要歌词**：`config.json → media.auto_show` / `media.lyrics` 改为 false。
- **蓝牙磁贴是灰色**：电脑没有蓝牙适配器或驱动不支持系统开关，点击会打开系统蓝牙设置。
- **热键无效**：可能被其他软件占用，在 `config.json → hotkeys` 里改。

## 效果图

<p align="center">
<img src="docs/compact_clock.png" height="56">&nbsp;
<img src="docs/compact_music.png" height="56">&nbsp;
<img src="docs/compact_pet.png" height="56">
</p>

<p align="center"><img src="docs/expressions.png" width="860"></p>

<p align="center"><img src="docs/subtitles.png" width="600"></p>

<p align="center">
<img src="docs/theme_light.png" width="280">
<img src="docs/theme_rouge.png" width="280">
<img src="docs/theme_sky.png" width="280">
</p>

---

## 在自己 fork 里开发时，怎么跟上原作者

把原作者仓库设为 `upstream`，自己的 fork 保持叫 `origin`（只需配置一次）：

```bash
git remote add upstream https://github.com/AsamiAkito/wisland
git remote -v                      # origin = 你的 fork，upstream = 原作者
```

之后同步：

```bash
git fetch upstream
git merge upstream/main            # 有冲突就解完再 commit；喜欢线性历史可以用 git rebase upstream/main
git push origin main
```

只想拿走某个修复而不合并全部时，用 cherry-pick：

```bash
git fetch upstream
git log --oneline upstream/main    # 找到那个提交
git cherry-pick <commit>
```

---

实时字幕与单词本流水线移植自 [YishengTranslator-White](https://github.com/kayson-39/YishengTranslator-White)（MIT）。MIT License.
