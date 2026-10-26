# Z6III 机内试装与验收

本页提供现在就能做的机内试装路径，但**不把社区配方等同于富士/理光原机色彩**。自主制作的五款验证版 NP3 尚未完成。

## 现成的三款社区试用基线

[Nikon-Recipes 的 Filmstill 目录](https://github.com/shouryan01/Nikon-Recipes/tree/2458e53bd07538749d3a30b5a6360f8ae18996e2/Third%20Party%20Creators/Filmstill) 含以下三个第三方文件。本项目只给原仓链接，不再打包其文件；下载前核对来源。

| 想试的风格 | 原仓文件 | 当前证据 |
|---|---|---|
| CC / 经典正片 | `Classic Chrome.NP3` | 文件存在，本项目未在 Z6III 验证 |
| NC / 经典负片 | `Filmstill's Classic Neg.NP3` | 文件存在，本项目未在 Z6III 验证 |
| NN / 怀旧负片 | `FIlmstill's Nostalgic Negative.NP3` | 文件存在，本项目未在 Z6III 验证；富士官方 LUT 包无 NN |

目前没有可核实来源、已验证兼容 Z6III 的理光 GR III Positive Film / Negative Film NP3 可供本项目推荐；这两款需要按下述实验链重新建立，不应把同名任意文件标成理光原厂。

## 在相机里试装

1. 保留原始文件副本和文件名，准备相机可读的存储卡。在电脑上把 `.NP3` 放到卡根目录，或 `NIKON/CUSTOMPC/`。如双卡，插入相机菜单设置的**主插槽**。
2. 相机菜单进入“照片拍摄菜单 → 管理优化校准 → 载入/保存 → 复制到照相机”，选择文件和 C-1 至 C-9 空槽。若菜单显示不兼容或无法识别，记录相机固件、文件名及提示；不要尝试修改固件。
3. 选定该自定义优化校准后拍 RAW+JPEG。固定白平衡和曝光；另拍相同设置的尼康中性基准。先用日光街景、肤色、绿植各一组，不以取景器预览代替文件比较。
4. 在 `data/manifests/captures.csv` 登记固件、文件哈希、场景、WB、曝光、槽位及导入结果。记录“能导入”“能拍摄”“色彩接近目标”三个不同结论。

以上卡路径、主插槽规则、C-1 至 C-9 槽位和“灵活颜色配置不能在机内编辑/重命名”来自[尼康 Z6III 官方说明](https://onlinemanual.nikonimglib.com/z6III/en/picture_controls_40.html)。

## 本项目五款正式版的门槛

CC/NC 先对官方 LUT 建立满足 F-Log2C/F-Gamut C 输入条件的电脑参考；NN 和理光正/负片先有明确机型、版本、设置和参考样本。随后用 NX Studio 的 Flexible Color 调整/导出 NP3，再经软件回读和 Z6III 真机 JPEG 比较。每款分别记完整文件来源、参数、误差与适用场景。只有完成这条链，才进入公开的 `release/`。
