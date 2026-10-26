# 尼康 Z6III × 富士胶片模拟研究

创建日期：2026-10-24。设备：用户自述中国大陆国行 Nikon Z6III；实际固件版本尚未读取，按用户要求以最新官方 C 2.01 为研发目标（2026-10-26 核实）。

目标：尽量保留富士原厂胶片模拟的色彩与明暗关系，同时量化尼康机内直出的可达程度。

本项目为独立研究，与 Nikon、Fujifilm、Ricoh 无官方合作关系；品牌及风格名称仅用于说明比较目标。

推荐顺序：**官方 LUT 参考链路 → 尼康照片/视频输入适配 → NP3 机内拟合 → 有明确问题时使用 REA**。

当前已完成研究结构、来源核对、实验定义、采样表和本机依赖检查。官方 LUT 包及研究资料存于本地私有目录；原厂包经 ZIP 完整性和哈希检查。五个 Nikon NEF 已通过 Adobe DNG Converter 转成可读传感器像素，CC/NC 已有电脑端实验预览。另已生成 9 个用于验证导入和参数响应的 NP3 诊断配置，文件结构和参数回读检查通过；五款胶片 NP3 和真机验证尚未完成。

素材更新：已入库 4 张下载 JPEG 和 5 个新增 NEF，原文件均保留，项目副本通过哈希核对。五个 NEF 经 Adobe DNG Converter 16.5 转换后，均由 rawpy 读取到完整传感器马赛克；两批无同名配对。私人样片与转换报告留在本地未公开。

执行更新：富士官方 LUT v1.10 包与白皮书已取得，CC/NC 的参考 LUT 完成完整性和网格检查；NN 未在该官方包中。五个 NEF 已解码并生成 CC/NC 的**未标定实验预览**；诊断 NP3 已生成并检查，胶片风格 NP3 尚未完成。详见 [首轮执行记录](docs/06_首轮执行记录.md)与[RAW 转换记录](docs/09_RAW转换与桌面预览.md)。公开仓库以 `reports/public-status.md` 为当前进度说明。

## 从这里开始

1. [研究方案](docs/01_研究方案.md)：路线选择、阶段与停止条件。
2. [来源与核实](docs/02_来源与核实.md)：一手链接、版本差异与事实边界。
3. [拍摄与验收](docs/03_拍摄与验收.md)：如何准备能用于验证的照片。
4. [REA 调查任务](docs/04_REA调查任务.md)：什么时候值得用逆向工具。
5. [准备状态与下一步](docs/05_准备状态与下一步.md)：已有条件、缺失资料、执行顺序。
6. [实验登记](experiments/experiments.json)。个人素材登记 `data/manifests/captures.csv` 仅保存在本地。
7. [Z6III 机内试装流程](docs/07_Z6III机内试装流程.md)：已有社区配方的试用边界、存储卡路径及拍摄记录。
8. [颜色输入契约](docs/08_颜色输入契约.md)：官方 CC/NC LUT 要求的 F-Gamut C、F-Log2C 条件。
9. [RAW 转换与桌面预览](docs/09_RAW转换与桌面预览.md)：五张 NEF 的实际解码结果和预览的技术局限。
10. [Z6III C 2.01 机内诊断包](docs/10_机内诊断包.md)：九个单项参数 NP3，首次只测试中性与饱和度两个文件。

## 目录

```text
docs/                      方案、证据、采样与交接
references/official/        已取得的富士原始 ZIP、技术文档；私有，不提交
references/community/       已取得的第三方源码/配置快照；私有，不提交
data/originals/nikon/       Z6III 原片，入库后不覆盖
data/originals/fuji/        可选富士同场景 RAW/JPEG，尚无
data/manifests/             素材与下载登记 CSV
data/derived/               中间图像和测试图，与原片隔离
experiments/                实验定义和运行记录
outputs/desktop/            电脑端参考结果
outputs/np3/                待验证的机内配置
outputs/comparisons/        对比图和盲评表
tools/                     本地准备检查脚本
configs/                   自主编写的 NP3 诊断参数源
third_party/               固定提交的 MIT NP3 库，保留版权与许可
reports/                   环境检查、验证结果
```

## 事实边界

- 富士官方公开的是规定输入条件下的 LUT，不是完整相机成像引擎源码。
- “使用原厂 LUT”“接近富士某台相机 JPEG”“尼康机内近似”是三种不同成果，分别记录。
- `.cube` 不应被直接重命名成 `.NP3`。NP3 拟合不是无损格式转换。
- 不以“导入成功”证明色彩一致，不承诺百分之百还原或没有测量依据的相似度。
- 本阶段没有修改相机或下载刷机包。第三方风格配方只是个人试用基线；自主生成的诊断 NP3 不属于五款胶片成品。

## 重新检查环境

NP3 诊断工具需要 Node.js 22.23.3 或更高、支持 TypeScript 类型擦除的版本；无需 npm 安装。先运行：

```powershell
node --experimental-strip-types tools/test_np3.mjs
node --experimental-strip-types tools/np3_tool.mjs build-lab
```

Python 工具使用 Python 3.12、numpy、Pillow；RAW 实验还需要 rawpy，Adobe DNG Converter 需另从官方取得。官方 LUT、样片和软件安装包均不随本仓库提供。执行 `python tools/package_calibration.py` 可打包诊断文件，生成物位于本地 `outputs/`。

在 PowerShell 中执行（脚本只读取环境、在本项目 reports 写入报告）：

```powershell
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$env:PYTHONIOENCODING = 'utf-8'
python tools/preflight.py
```
