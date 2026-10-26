# 第二轮执行记录：RAW 转换与桌面预览（2026-10-24）

## 真正读到了 RAW 像素

- 从 [Adobe 官方 DNG Converter](https://helpx.adobe.com/camera-raw/desktop/dng-and-file-formats/adobe-dng-converter.html)取得 Windows x64 16.5 安装包：1,205,672,880 字节，SHA-256 `F8AA90D62D78E75C432565C54256EE1D8FC9E1922BC5DF0E012236ADA320D33C`。Windows Authenticode 状态为 Valid，签名者 Adobe Inc.；原安装包私有保存、不随仓库发布。
- 本机 Windows 10 使用官方程序的命令行模式，将五张用户下载的 Z6III NEF 逐张转为**无损压缩马赛克 DNG**，不嵌入原 NEF，也不覆盖原件。脚本为 `tools/convert_nef_to_dng.py`，参数和输出哈希见本地私有 `reports/dng-conversion.json`。
- 五个 DNG 均由项目私有 `rawpy 0.27.1` 读到 4040×6064 的 `uint16` 可见传感器马赛克；按间隔采样的标准差均大于 500，排除了空白像素阵列。这里验证的是 RAW 马赛克可读，不代表 Adobe 与尼康自己的显影颜色一致。
- DNG 为私有派生文件，`.gitignore` 排除在 GitHub 外。

## CC/NC 实验性桌面预览

`tools/preview_dng_official_lut.py` 对 DNG 使用固定的 LibRaw 相机白平衡、关闭自动提亮、线性 sRGB 16 位半尺寸显影，然后按 D65 原色矩阵转换到 F-Gamut C，经白皮书 F-Log2C 曲线送入官方 65 网格 CC/NC LUT。五张均顺利输出对照图片。本地汇总图在 `outputs/comparisons/all-5-dng-experimental-exp2.jpg`，属于私有样片，不随仓库发布。

首轮试验统一指定 `--exposure-stops 2` 以便目视检查。**这不是标定值**。以 `DSC_0013` 为例，加曝后的普通线性 sRGB 显示基准有约 6.44% 像素至少一通道到达 1.0；CC/NC 结果的曝光与高光不能据此判定准确。sRGB 中间空间可能先剪掉宽色域信息；相机白平衡、RAW 矩阵和色彩适应也未经色卡确认。预览只能说明桌面链路可运行，并初步观察两个官方 LUT 的方向，不能证明“富士原汁原味”或 Nikon 机内表现。

2026-10-26 补核全批：统一 +2 EV 的普通 sRGB 显示对照触顶比例依次约为 6.44%、85.82%、76.20%、16.32%、50.53%，因此不能作为可靠的显示对照。另以每个 NEF 内嵌同场景 JPEG 的全图显示亮度中位数估计增益，结果如下。该方法仅是亮度启发式，未解决高光映射差异。

| 文件 | JPEG 中位数匹配的加曝档数 | 普通 sRGB 显示对照触顶像素 |
|---|---:|---:|
| DSC_0013 | +1.177 | <0.001% |
| DSC_0078 | +1.101 | 38.29% |
| DSC_0207 | +1.275 | 50.04% |
| DSC_0299 | +1.434 | 0.50% |
| DSC_2008 | +1.515 | 33.37% |

**这里的触顶发生在普通 sRGB 显示对照支路**：它直接把大于 1 的场景数值裁到 1，没有高光压缩。官方 LUT 支路把加曝后的值先做 F-Log2C 编码，允许场景值大于 1；本批测得越出 LUT 编码域的比例为零。因此不能把表中比例解释为同等数量的 LUT 输入像素被裁掉，也不能据此断言 LUT 本身失败。真正未解决的是 RAW 到反射率的曝光基准、Nikon 相机矩阵误差和已在 LibRaw sRGB 输出阶段发生的色域损失。单个曝光增益无法补齐这些问题；后续拟合不采用这两种未标定预览作为真值。

五张现有 RAW 主要覆盖日光蓝天、湖水、灰岩和草地，缺少可用于标定的灰卡、近景肤色、暖光与夜景。下一步要用固定曝光/白平衡的 RAW+JPEG 对照和已知参考目标校准照片输入，然后在 NX Studio 的 Flexible Color 参数空间尝试拟合。受本机 Windows 10 与当前 NX Studio Windows 11 要求的差异影响，NP3 软件回读需在符合要求的环境完成，再进入 Z6III 真机导入与拍摄验证。
