# -*- coding: utf-8 -*-
"""C75 模块 02 · 稠密多视图立体：代价体、平面扫掠、光度一致性。"""
from coursekit import P, H3, DUAL, CALLOUT, ASCII, CODE, MATH, TABLE, UL, OL, md, code

META = [
    ("本模块回答", "① 代价体的三个维度各由什么决定（1920×1080×256 = <strong>2.12 GB</strong>）；"
                   "② <strong>为什么深度假设必须在<em>视差</em>上均匀</strong>——"
                   "深度均匀时 $D{=}64$ 在近场的视差步长是 <strong>102.7 px</strong>；"
                   "③ 所需假设数的闭式 $D = fB(1/z_{\\min}-1/z_{\\max})$；"
                   "④ <strong>光度一致性的三类失效，而它们的<em>签名</em>不同</strong>："
                   "弱纹理随噪声渐进失效、周期纹理<strong>与噪声无关</strong>地结构性失效、"
                   "无纹理区给出「看起来可信但纯是噪声」的数；"
                   "⑤ <strong>窗口大小没有通用答案</strong>（同一张表里 win41 在一处是唯一可用的、"
                   "在另一处 100% 失败）；"
                   "⑥ 前平行假设与视差梯度 $\\mathrm dd/\\mathrm du = -(B/z)\\tan\\theta$"),
    ("配套 notebook", '<span class="badge cpu">CPU</span> 02_mvs.ipynb'
                       '（<strong>视差域 vs 深度域采样的逐档对比</strong> / '
                       'NCC 与峰-次峰间隔 / '
                       '<strong>周期纹理的误差恰好等于一个周期，且与噪声无关</strong> / '
                       '窗口 × 纹理 × 倾斜的完整取舍表 / '
                       '<strong>倾斜反而修好周期纹理</strong> / 左右一致性检验）'),
    ("核心参考", "Furukawa &amp; Hernández, <em>Multi-View Stereo: A Tutorial</em>（2015）· "
                 "Collins, <em>A Space-Sweep Approach to True Multi-Image Matching</em>（CVPR 1996，平面扫掠的出处）· "
                 "Hirschmüller, <em>Stereo Processing by Semiglobal Matching</em>（TPAMI 2008，SGM）· "
                 "Bleyer et al., <em>PatchMatch Stereo</em>（BMVC 2011，斜面假设）· "
                 "Schönberger et al., <em>Pixelwise View Selection for Unstructured MVS</em>（ECCV 2016，COLMAP 的 MVS）· "
                 "Burt &amp; Julesz, <em>A Disparity Gradient Limit for Binocular Fusion</em>（Science 1980）· "
                 "本课程 <strong>C72</strong> 模块 03（三角测量的 $Z^2$ 律）"),
    ("预计时长", "读 55 分钟 + 跑 50 分钟"),
]

SECTIONS = [
    # ============================================================== 1
    ("cost-volume", "代价体：三个维度，三种成本", "".join([
        P("稠密立体的标准结构是**代价体**（cost volume）："
          "对每个像素、每个深度假设，存一个「这个假设有多可信」的代价。"),
        ASCII("""
   代价体 C[v][u][d]  —— 三个维度：

      u, v : 参考图像的像素          -> 由分辨率决定
      d    : 深度（或视差）假设的编号  -> 由第 2 节的公式决定

   平面扫掠（plane sweep）的做法：
      for each 深度假设 d:
          把每张源图像按「场景在深度 d 的平面上」这个假设投影到参考视角
          （一次单应变换 H_d —— 见 C72 模块 03）
          算参考图与投影图的光度一致性  ->  填进 C[:,:,d]

   然后：WTA（取每个像素代价最小的 d）+ 亚像素插值 + 一致性滤波
        """),
        TABLE(["分辨率", "$D{=}64$", "$D{=}128$", "$D{=}192$", "$D{=}256$"], [
            ["640×480", "0.079 GB", "0.157 GB", "0.236 GB", "0.315 GB"],
            ["1280×720", "0.236 GB", "0.472 GB", "0.708 GB", "0.944 GB"],
            ["<strong>1920×1080</strong>", "0.531 GB", "1.062 GB", "1.593 GB",
             "<strong>2.123 GB</strong>"],
        ]),
        DUAL(
            "<strong>2.12 GB 只是<em>存</em>代价体，而实际流程里还要存聚合后的代价体、"
            "以及每个源图像的一份中间结果。</strong>"
            "<em>所以真实的 MVS 实现几乎都不会把完整代价体驻留在内存里</em>——"
            "<strong>常见做法是按深度切片流式处理（算完一片就聚合掉）、"
            "或按图像块（tile）分治</strong>。"
            "<em>这与 C74 模块 03 里 3DGS 按 tile 组织是同一个动机：把工作集压进缓存</em>。",
            "<strong>而三个维度的成本性质不同：</strong>"
            "<em>分辨率降一半 → 体积降 4 倍，但深度精度不变（视差范围也降一半，"
            "所以 $D$ 可以同时降一半 → 实际降 8 倍）；"
            "$D$ 降一半 → 体积降 2 倍，而<strong>深度分辨率直接降一半</strong></em>。"
            "<strong>所以「降分辨率」比「降 $D$」划算得多</strong>——"
            "<em>这就是 MVS 普遍先在低分辨率上算、再逐级上采样细化（coarse-to-fine）的原因</em>。"),
    ])),

    # ============================================================== 2
    ("sampling", "深度假设必须在<em>视差</em>上均匀", "".join([
        P("一个很自然但错误的做法：把 $[z_{\\min}, z_{\\max}]$ 均匀切成 $D$ 份。"
          "**错在哪：测量量是视差，而视差与深度是倒数关系。**"),
        MATH(r"d = \frac{fB}{z}\;\Longrightarrow\;"
             r"\Delta d = \frac{fB}{z^2}\Delta z"),
        P("取 $f{=}700$ px、$B{=}0.12$ m、深度范围 $[0.5, 50]$ m"
          "（对应视差范围 $[1.68, 168]$ px，跨 100 倍）："),
        TABLE(["采样方式", "$D$", "最大深度间隔 $\\Delta z$", "视差步长"], [
            ["深度均匀", "64", "0.786 m @ z=36.6 m",
             "<strong>最大 102.667 px @ z=1.29 m</strong>"],
            ["深度均匀", "256", "0.194 m @ z=8.1 m",
             "<strong>最大 46.983 px @ z=0.69 m</strong>"],
            ["<strong>视差均匀</strong>", "64", "30.6 m @ z=50 m",
             "<strong>恒为 2.640 px</strong>"],
            ["<strong>视差均匀</strong>", "256", "13.98 m @ z=50 m",
             "<strong>恒为 0.652 px</strong>"],
        ]),
        DUAL(
            "<strong>深度均匀采样在近场是灾难性的：$D{=}64$ 时 $z{=}1.29$ m 附近"
            "相邻两个假设差 <em>102.7 px</em> 的视差。</strong>"
            "<em>而一个像素的匹配代价在 100 px 的跨度上早就没有相关性了——"
            "所以近场等于<strong>完全没采样</strong></em>。"
            "<strong>即使把 $D$ 加到 256，最坏处仍有 47 px。</strong>",
            "<strong>视差均匀的代价是<em>远场</em>粗：$z{=}50$ m 附近相邻假设差 30.6 m。</strong>"
            "<em>但这是<strong>正确</strong>的取舍——因为 $\\sigma_z = z^2\\sigma_d/(fB)$，"
            "$z{=}50$ m 处 0.5 px 的测量噪声本身就对应 14.9 m 的深度不确定度</em>。"
            "<strong>所以「远场粗」不是采样的损失，它匹配了测量精度本身的分布。</strong>"
            "<em>换句话说：在视差上均匀采样 = 让每个假设承担<strong>相同的信息量</strong></em>。"),
        H3("需要多少个假设：一个闭式"),
        MATH(r"D_{\text{需要}} = \left\lceil fB\left(\frac{1}{z_{\min}}-\frac{1}{z_{\max}}\right)\right\rceil + 1"
             r"\qquad(\text{视差步长} \le 1\text{ px})"),
        TABLE(["场景", "$f$ (px)", "$B$ (m)", "深度范围", "视差范围 (px)", "<strong>需要的 $D$</strong>"], [
            ["手持双目 / 相邻帧", "700", "0.12", "[0.5, 50] m", "[1.68, 168]", "<strong>168</strong>"],
            ["同上，近场收紧", "700", "0.12", "[1.0, 20] m", "[4.20, 84]", "81"],
            ["车载双目", "1200", "0.50", "[2.0, 80] m", "[7.50, 300]", "<strong>294</strong>"],
            ["宽基线航拍", "500", "6.00", "[3.0, 20] m", "[150, 1000]", "<strong>851</strong>"],
            ["手机双摄（微距）", "700", "0.03", "[0.3, 5] m", "[4.20, 70]", "67"],
        ]),
        CALLOUT("intuition",
                "<strong>这个式子有一个直接的工程用途：<em>反推该把 $z_{\\min}$ 设在哪</em>。</strong>"
                "<em>$D$ 与 $1/z_{\\min}$ 成正比，所以把最近深度从 0.5 m 放宽到 1.0 m，"
                "$D$ 从 168 降到 81（少一半）</em>。"
                "<strong>而宽基线航拍那一行的 851 说明：基线越长虽然深度越准，"
                "但代价体也越大</strong>——"
                "<em>$D \\propto B$，而这与第 6 节「基线越长前平行假设越容易破」是同一个张力的两面</em>。"),
    ])),

    # ============================================================== 3
    ("photometric", "光度一致性的三类失效，而签名各不相同", "".join([
        P("代价函数通常是 NCC（归一化互相关）或它的变体。"
          "notebook 用 1D 扫描线做了受控实验："
          "同一个真值视差 7.0 px、窗口 21 px、噪声 $\\sigma{=}0.01$，只换纹理类型："),
        TABLE(["纹理类型", "梯度能量", "峰值 NCC", "次峰 NCC",
               "<strong>峰-次峰间隔</strong>", "argmax 偏差"], [
            ["宽带纹理（rich）", "$1.41$", "1.0000", "0.5308",
             "<strong>0.4692</strong>", "+0.000 px"],
            ["弱纹理（weak）", "$2.01\\times10^{-3}$", "0.9990", "0.9740",
             "<strong>0.0249</strong>", "+0.000 px"],
            ["无纹理（flat）", "$2.00\\times10^{-6}$", "0.6266", "0.5106",
             "0.1160", "<strong>−0.250 px（这次碰巧接近真值）</strong>"],
            ["周期纹理（周期 16 px）", "$7.61\\times10^{-2}$", "1.0000", "1.0000",
             "<strong>0.0000</strong>", "<strong>+16.000 px</strong>"],
        ]),
        CALLOUT("warn",
                "<strong>无纹理那一行的 −0.250 px 是一个陷阱：它碰巧接近真值。</strong>"
                "<em>notebook 跨 300 个种子重跑：RMS 误差 <strong>18.50 px</strong>、"
                "标准差 <strong>17.44</strong>——"
                "而「均匀分布在整个假设范围 $[-30,30]$」的标准差是 <strong>17.32</strong></em>。"
                "<strong>也就是说它的输出与随机猜<em>不可区分</em></strong>"
                "（$\\vert$误差$\\vert\\le1$ px 的比例 6.7%，随机基线 3.3%）。"
                "<em>所以这类实验必须跨多个种子看分布——单个种子会骗人，本例就骗了一次</em>。"),
        H3("噪声下的表现暴露了三种<em>不同</em>的失效机制"),
        TABLE(["纹理", "$\\sigma{=}0.01$ 的失败率", "$\\sigma{=}0.05$",
               "$\\sigma{=}0.2$", "$\\sigma{=}0.2$ 的 RMS", "机制"], [
            ["rich", "0%", "0%", "0%", "0.018 px", "<strong>不失效</strong>"],
            ["weak", "0%", "<strong>18%</strong>", "<strong>74%</strong>",
             "8.994 px",
             "<strong>随噪声渐进失效</strong>——间隔 0.0249 很快被噪声吃掉"],
            ["periodic", "<strong>76%</strong>", "74%", "69%", "18.802 px",
             "<strong>与噪声无关的结构性失效</strong>"],
        ]),
        DUAL(
            "<strong>周期纹理那一行是本节最重要的一条：它在 $\\sigma{=}0.01$ 时就已经 76% 错，"
            "而加噪到 20 倍<em>不改变</em>失败率。</strong>"
            "<em>而误差是 <strong>+16.000 px</strong>——恰好一个周期</em>。"
            "<strong>所以它不是「精度不够」，而是「有多个完全等价的解」。</strong>"
            "<em>这与模块 01 第 6 节共面场景的签名完全一致："
            "$E$ 的方向误差在 0.2 px 与 1.0 px 噪声下都是 3.15°</em>。"
            "<strong>「加噪声不改变误差」= 结构性歧义。</strong>",
            "<strong>而无纹理区（flat）是最危险的一类，因为它<em>不报错</em>。</strong>"
            "<em>NCC 的分母是窗内标准差；只要有一点噪声（这里 $10^{-3}$）分母就不为 0，"
            "于是你得到一个 0.669 的「相关性」和一个 $-31.5$ px 的视差</em>。"
            "<strong>它看起来是一个有效的测量，实际上纯是噪声。</strong>"
            "<em>所以 MVS 必须<strong>显式</strong>剔除低纹理区（按梯度能量或按峰-次峰间隔），"
            "而不能指望代价函数自己报告「我不知道」</em>。"),
        CALLOUT("danger",
                "<strong>一个直接可用的置信度：峰-次峰间隔（peak ratio / margin）。</strong>"
                "<em>上表里它把三类完美分开：rich 0.474、weak 0.027、periodic 0.000</em>。"
                "<strong>而它比「峰值 NCC」有用得多</strong>——"
                "<em>weak 与 periodic 的<strong>峰值</strong>都是 0.99 以上（看起来极好），"
                "只有间隔能区分它们</em>。"
                "<strong>这也是 SGM 与 PatchMatch 类方法都会输出一个「唯一性比」的原因。</strong>"),
    ])),

    # ============================================================== 4
    ("window", "窗口大小：没有通用答案", "".join([
        P("窗口越大，统计越稳（对弱纹理有利）；但窗口越大，"
          "「窗内视差恒定」这个假设越容易被破坏（对倾斜表面不利）。"
          "notebook 把这两件事放进一张表——每格是 100 次试验里 $|$误差$|>1$ px 的比例，"
          "噪声 $\\sigma{=}0.05$："),
        TABLE(["视差梯度", "窗口", "rich", "weak", "periodic"], [
            ["<strong>0.0</strong>", "5", "1%", "97%", "74%"],
            ["", "9", "0%", "89%", "69%"],
            ["", "21", "0%", "19%", "74%"],
            ["", "<strong>41</strong>", "0%", "<strong>0%</strong>", "85%"],
            ["<strong>0.1</strong>", "5", "20%", "97%", "72%"],
            ["", "9", "<strong>0%</strong>", "89%", "79%"],
            ["", "21", "<strong>0%</strong>", "37%", "21%"],
            ["", "<strong>41</strong>", "<strong>100%</strong>", "2%", "36%"],
            ["<strong>0.3</strong>", "5", "100%", "97%", "75%"],
            ["", "9", "100%", "89%", "97%"],
            ["", "21", "100%", "68%", "<strong>7%</strong>"],
            ["", "41", "97%", "98%", "<strong>1%</strong>"],
        ]),
        DUAL(
            "<strong>看两个格子就够了：</strong>"
            "<em>视差梯度 0 时，弱纹理<strong>只有</strong> win41 能用（0% vs win21 的 19%）；"
            "而视差梯度 0.1 时，宽带纹理用 win41 是 <strong>100% 失败</strong>"
            "（而 win9 与 win21 都是 0%）</em>。"
            "<strong>同一个窗口尺寸，在一处是唯一可用的、在另一处是唯一不可用的。</strong>"
            "<em>所以「用 $k\\times k$ 的窗口」这句话本身就不完整——它必须依赖局部内容</em>。",
            "<strong>这就是三代方法的分界线：</strong>"
            "<em>① 固定窗口（经典块匹配）——只能在「纹理够 + 表面正对」的区域可靠；"
            "② <strong>自适应窗口 / 自适应权重</strong>（bilateral、guided）——按图像内容改形状；"
            "③ <strong>斜面假设</strong>（PatchMatch Stereo）——"
            "把每个像素的假设从「一个深度」换成「一个 3D 平面（深度 + 两个梯度）」，"
            "于是窗内视差可以线性变化，前平行假设整体消失</em>。"
            "<strong>代价是搜索空间从 1 维变成 3 维，所以只能用随机化传播（PatchMatch）而不能穷举。</strong>"),
        H3("一条反直觉的结果：倾斜<em>修好</em>了周期纹理"),
        P("上表 periodic 一列：视差梯度 0 时是 74–85% 失败，"
          "而视差梯度 0.3 + win21 时降到 **7%**、win41 降到 **1%**。"),
        CALLOUT("intuition",
                "<strong>原因很干净：窗内视差线性变化时，周期图案不再能在「偏移一个周期」处对齐。</strong>"
                "<em>正对相机的周期栅栏是最难匹配的；一旦它斜过来，"
                "每一列的视差都不同，歧义就被打破了</em>。"
                "<strong>所以斜面假设（③）不只是「修好倾斜」，它顺带修好了一类周期歧义</strong>——"
                "<em>而这在只做「窗口自适应」的方法（②）里拿不到</em>。"),
    ])),

    # ============================================================== 5
    ("gradient-limit", "视差梯度：把倾斜换算成一个可比的量", "".join([
        MATH(r"d = \frac{fB}{z},\quad \frac{\mathrm dz}{\mathrm du} = \tan\theta\cdot\frac{z}{f}"
             r"\;\Longrightarrow\;"
             r"\boxed{\frac{\mathrm dd}{\mathrm du} = -\frac{B}{z}\tan\theta}"),
        P("$\\theta$ 是表面相对「正对相机」的倾角。"
          "所以**同一个视差梯度对应的物理倾角取决于 $B/z$**："),
        TABLE(["视差梯度 $\\vert \\mathrm dd/\\mathrm du\\vert$", "$B/z{=}0.05$",
               "$B/z{=}0.2$", "$B/z{=}1.0$", "$B/z{=}2.0$"], [
            ["0.05", "45.0°", "14.0°", "2.9°", "1.4°"],
            ["0.15", "71.6°", "36.9°", "8.5°", "4.3°"],
            ["0.30", "80.5°", "56.3°", "<strong>16.7°</strong>", "<strong>8.5°</strong>"],
            ["1.00（融合极限）", "87.1°", "78.7°", "45.0°", "26.6°"],
        ]),
        DUAL(
            "<strong>读法：第 4 节那张表里「视差梯度 0.3」这一档，</strong>"
            "<em>在窄基线（$B/z{=}0.05$，如手持相邻帧）下对应 80.5° 的倾角——"
            "几乎侧着，很罕见；"
            "而在宽基线（$B/z{=}2.0$，如航拍）下只对应 <strong>8.5°</strong>——"
            "几乎任何真实表面都超过它</em>。"
            "<strong>所以宽基线的代价不只是「代价体变大」（第 2 节的 $D{=}851$），"
            "更是「前平行假设几乎必然被破坏」。</strong>",
            "<strong>而 $\\vert\\mathrm dd/\\mathrm du\\vert = 1$ 是一个有名的界：</strong>"
            "<em>人类双目融合的<strong>视差梯度极限</strong>约为 1（Burt &amp; Julesz, 1980）——"
            "超过它两只眼睛就融不上，看到的是双影</em>。"
            "<strong>几何含义是「表面与两条视线之一平行」</strong>："
            "<em>此时表面在一只眼里被压缩到零宽度</em>。"
            "<strong>所以这不是生理限制，是几何限制——任何立体方法都撞在同一个界上。</strong>"),
        CALLOUT("paper",
                "<strong>把第 2 节与本节合起来，就得到宽基线 MVS 的完整取舍：</strong>"
                "<em>$B$ 增大 → 深度精度 $\\propto 1/B$ 变好（C72 的 $Z^2$ 律）"
                "→ 但代价体 $D \\propto B$ 变大 "
                "→ 而且视差梯度 $\\propto B/z$ 变大、前平行假设变差</em>。"
                "<strong>所以实践中的做法是「多组中等基线」而不是「一组大基线」</strong>——"
                "<em>COLMAP 的 MVS 就是逐像素挑选一组源图像（pixelwise view selection），"
                "而挑选的判据里同时含基线角度与光度一致性</em>。"),
    ])),

    # ============================================================== 6
    ("multiview", "多视角聚合：它修好的不只是噪声", "".join([
        P("前面几节都是两视图。而 MVS 的 M 指的是把**多个**源视图的代价聚合起来。"
          "notebook 用「每个源视图的基线比例在 0.6–1.4 之间」（模拟真实的不等基线）来测："),
        TABLE(["纹理", "视图数", "峰-次峰间隔", "失败率（$\\sigma{=}0.05$）"], [
            ["rich", "1 → 8", "0.4692 → <strong>0.8807</strong>（单调变好）", "0% → 0%"],
            ["weak", "1", "0.0249", "<strong>22%</strong>"],
            ["", "2", "0.1111", "<strong>0%</strong>"],
            ["", "8", "0.0606", "0%"],
            ["<strong>periodic</strong>", "<strong>1</strong>", "<strong>0.0000</strong>",
             "<strong>71%</strong>"],
            ["", "<strong>2</strong>", "<strong>0.1550</strong>", "<strong>0%</strong>"],
            ["", "4", "0.7149", "0%"],
        ]),
        DUAL(
            "<strong>周期纹理那两行是本节的重点：一个视图 80% 失败，"
            "<em>两个</em>视图 0% 失败。</strong>"
            "<em>而原因不是「数据变多了」——是<strong>结构性歧义被打破了</strong>："
            "两个源视图的基线不同，所以「偏移一个周期」在它们各自的视差坐标里"
            "对应<strong>不同</strong>的假设编号，于是错误峰不重合、真峰重合</em>。"
            "<strong>这是多视图立体优于双目立体的<em>本质</em>原因，而不只是精度上的改善。</strong>",
            "<strong>而这已经是本模块里修好周期纹理的<em>第三</em>条路：</strong>"
            "<em>① 第 4 节：表面倾斜（视差梯度 0.3 + win41 → 失败率 1%）；"
            "② 第 7 节：非局部先验（SGM 的路径代价）；"
            "③ 本节：不等基线的多视角聚合（2 个视图就够）</em>。"
            "<strong>三条路的共同点是「引入一个让两个候选解不再等价的额外约束」</strong>——"
            "<em>而第三条最便宜，因为多视角本来就有</em>。"),
        H3("注意 weak 那三行：失败率变好，而间隔<em>没有</em>单调变好"),
        P("弱纹理的间隔从 2 视图的 0.1113 掉到 8 视图的 0.0610，"
          "但失败率从 2% 降到 0%。**这不矛盾**："
          "聚合同时做了两件事——改变代价曲线的**形状**（间隔），"
          "以及降低曲线上的**噪声**。对弱纹理，第二件事的收益更大。"),
        H3("聚合方式：「要求所有视图都同意」是最<em>不</em>稳健的"),
        P("遮挡是 MVS 的常态：某个源视图里，这个点根本看不见。"
          "notebook 构造了「8 个源视图里有 $k$ 个被遮挡（代价是纯噪声）」，"
          "比较三种聚合："),
        TABLE(["被遮挡的视图数（共 8）", "均值（mean）", "中位数（median）",
               "最小值（min，即「所有视图都同意」）"], [
            ["0", "0%", "0%", "0%"],
            ["<strong>1</strong>", "<strong>0%</strong>", "<strong>0%</strong>",
             "<strong>28%</strong>"],
            ["2", "0%", "0%", "<strong>59%</strong>"],
            ["4", "<strong>0%</strong>", "0%", "<strong>70%</strong>"],
            ["6", "<strong>24%</strong>", "80%", "95%"],
        ]),
        CALLOUT("danger",
                "<strong>直觉会说「取最小值最保守、最安全」，而实测正相反：</strong>"
                "<em>min 在只有 <strong>1/8</strong> 个视图被遮挡时就 28% 失败、2/8 时 59%，"
                "而均值在 4/8 被遮挡时仍是 0%</em>。"
                "<strong>而 6/8 时的排序是 mean 24% &lt; median 80% &lt; min 95%——"
                "连中位数都不如均值。</strong>"
                "<strong>因为 min 完全由<em>最差</em>的那个视图决定——"
                "一个被遮挡的视图就能把真峰按下去。</strong>"
                "<em>「保守」在这里等于「对离群点零容忍地敏感」</em>。"
                "<strong>所以真实的 MVS 不用 min，而是"
                "「先<em>挑</em>视图，再对挑出的做（稳健）均值」</strong>——"
                "<em>COLMAP 的 pixelwise view selection 就是这一步，"
                "而它的判据同时含基线角度（第 5 节）与光度一致性（第 3 节）</em>。"),
    ])),

    # ============================================================== 7
    ("to-depth", "从代价体到深度图：WTA 之后还有三步", "".join([
        OL([
            "<strong>WTA（取每像素代价最优的假设）</strong>——"
            "<em>只给出整数级的视差，而第 2 节说步长可能就是 1 px，"
            "所以直接用会有明显的阶梯（量化到 $\\sigma_z = z^2/(fB)$ 的量级）</em>",
            "<strong>亚像素插值</strong>——"
            "<em>用最优假设及其左右两个的代价做抛物线拟合，取顶点。"
            "典型能把视差精度做到 0.1–0.25 px</em>。"
            "<strong>但它有一个已知的偏置：抛物线拟合会把结果往整数位置吸引</strong>"
            "（<em>pixel-locking</em>）",
            "<strong>置信度滤波</strong>——"
            "<em>按第 3 节的峰-次峰间隔、以及梯度能量，把不可信的像素标成「无效」。"
            "<strong>标成无效比给一个错的深度好</strong>，因为下游（模块 05 的融合）能处理空洞，"
            "但处理不了自信的错误值</em>",
            "<strong>左右一致性检验</strong>——"
            "<em>以左图为参考算一次、以右图为参考再算一次，"
            "要求 $\\vert d_L(u) - d_R(u - d_L(u))\\vert < \\tau$（典型 $\\tau{=}1$ px）。"
            "<strong>它专门抓遮挡</strong>：被遮挡的像素在另一张图里根本不存在对应，"
            "所以两次估计必然不一致</em>",
        ]),
        DUAL(
            "<strong>第 4 步值得单独说，因为它是唯一能<em>检测</em>遮挡的便宜手段。</strong>"
            "<em>遮挡在代价体里的表现与弱纹理很像——代价曲线平、峰值低。"
            "但它的成因完全不同：不是「信息不足」，而是「对应根本不存在」</em>。"
            "<strong>而左右一致性能把这两者分开</strong>："
            "<em>弱纹理区两次估计会一致地错，遮挡区两次估计会不一致</em>。",
            "<strong>把这一节的四步与前面几节连起来，就是一张诊断表：</strong>"
            "<em>深度图有阶梯 → 缺第 2 步（或亚像素被 pixel-locking 吸住）；"
            "大片区域深度乱跳 → 第 3 步的阈值太松（第 3 节：无纹理区不报错）；"
            "物体边缘有一条错误的「拖尾」→ 缺第 4 步（遮挡未被剔除）；"
            "近场整体不对 → 第 2 节的采样问题</em>。"),
        CALLOUT("warn",
                "<strong>而有一类问题四步都修不了：周期结构。</strong>"
                "<em>栅栏、砖墙、键盘、百叶窗——它们的两次估计会<strong>一致地</strong>"
                "错到同一个周期上，所以左右一致性检验通不过它们</em>。"
                "<strong>唯一的办法是引入非局部信息</strong>："
                "<em>SGM 的路径代价、或者更大范围的平面/分割先验。"
                "而第 4 节那个「倾斜修好周期纹理」的观察给了第三条路："
                "斜面假设本身就打破了这类歧义</em>。"),
    ])),
]

# =====================================================================
NB = [
md("""# C75 · 模块 02 · 稠密多视图立体

本 notebook 把讲解页的六个结论跑出来：

1. 代价体的规模（1920×1080×256 = **2.12 GB**）；
2. **深度假设必须在视差上均匀** —— 深度均匀时 $D{=}64$ 的近场视差步长是 **102.7 px**；
3. **光度一致性的三类失效，签名各不相同**：
   弱纹理随噪声渐进失效、周期纹理**与噪声无关**、无纹理区**不报错**地给出噪声；
4. **窗口大小没有通用答案**（同一张表里 win41 在一处是唯一可用的、在另一处 100% 失败）；
5. **不等基线的多视角聚合彻底修好周期纹理**（1 视图 80% 失败 → 2 视图 0%）；
6. **「要求所有视图都同意」是最<em>不</em>稳健的聚合方式**；
7. 左右一致性检验为什么能抓遮挡、而抓不到周期结构。

只用 numpy，CPU，离线。全部实验在 1D 扫描线上做。"""),

code("""import numpy as np, math
print('numpy', np.__version__)

N_SIG = 4096
XS = np.arange(N_SIG)

def make_signal(kind, seed=0):
    '''四种 1D「纹理」。'''
    r = np.random.default_rng(seed)
    if kind == 'rich':          # 宽带
        s = np.zeros(N_SIG)
        for f in np.linspace(0.01, 0.35, 40):
            s += r.normal()*np.sin(2*np.pi*f*XS + r.uniform(0, 2*np.pi))
        return s/np.std(s)
    if kind == 'weak':          # 只有低频
        s = np.zeros(N_SIG)
        for f in np.linspace(0.002, 0.01, 6):
            s += r.normal()*np.sin(2*np.pi*f*XS + r.uniform(0, 2*np.pi))
        return s/np.std(s)
    if kind == 'flat':          # 无纹理（常数 + 极小噪声）
        return np.full(N_SIG, 1.0) + r.normal(0, 1e-3, N_SIG)
    if kind == 'periodic':      # 周期 16 px
        return np.sin(2*np.pi*XS/16.0)
    raise ValueError(kind)

def sample(sig, pos):
    '''线性插值采样。'''
    p = np.clip(pos, 0, N_SIG-2)
    i = np.floor(p).astype(int); f = p - i
    return sig[i]*(1-f) + sig[i+1]*f

def ncc(a, b):
    '''归一化互相关。窗内方差为 0 时返回 nan。'''
    a = np.asarray(a, float) - np.mean(a)
    b = np.asarray(b, float) - np.mean(b)
    da, db = np.std(a), np.std(b)
    if da < 1e-12 or db < 1e-12:
        return np.nan
    return float(np.mean(a*b)/(da*db))

HYPS = np.arange(-30, 30.25, 0.25)
print(f'假设网格：{len(HYPS)} 个，从 {HYPS[0]} 到 {HYPS[-1]}，步长 {HYPS[1]-HYPS[0]}')
for k in ['rich', 'weak', 'flat', 'periodic']:
    s = make_signal(k, 0)
    print(f'  {k:9s} 梯度能量 {np.mean(np.diff(s)**2):.3e}  标准差 {np.std(s):.4f}')"""),

md("""## 1 · 代价体的规模"""),

code("""print(' 分辨率        D=64      D=128     D=192     D=256   （fp32 内存）')
for W, H in [(640, 480), (1280, 720), (1920, 1080)]:
    row = '  '.join(f'{W*H*D*4/1e9:7.3f} GB' for D in [64, 128, 192, 256])
    print(f' {W}x{H:<5d} {row}')
assert abs(1920*1080*256*4/1e9 - 2.123) < 0.01
print('\\n✓ 1920x1080 x 256 = 2.12 GB —— 而实际流程还要存聚合后的体、以及每个源图的中间结果')
print('  所以真实实现按深度切片流式处理，或按图像块分治（与 C74 模块 03 的 tile 同一动机）')

print('\\n三个维度的成本性质不同：')
base = 1920*1080*256
print(f'  基准 1920x1080 x256: {base/1e6:.1f} M 体元')
print(f'  分辨率减半（视差范围也减半，所以 D 也减半）: '
      f'{960*540*128/1e6:.1f} M -> {base/(960*540*128):.0f} 倍')
print(f'  只把 D 减半: {1920*1080*128/1e6:.1f} M -> {base/(1920*1080*128):.0f} 倍'
      f'（而深度分辨率直接减半）')
assert base/(960*540*128) == 8.0
print('\\n✓ 降分辨率省 8 倍且深度精度不变；降 D 只省 2 倍且深度精度减半')
print('  -> 这就是 coarse-to-fine（先低分辨率再逐级细化）的理由')"""),

md("""## 2 · 深度假设必须在视差上均匀"""),

code("""def hypotheses(f, B, zmin, zmax, D, mode='disparity'):
    '''返回 D 个深度假设（升序）。'''
    if mode == 'depth':
        return np.linspace(zmin, zmax, D)
    if mode == 'disparity':
        d = np.linspace(f*B/zmax, f*B/zmin, D)
        return (f*B/d)[::-1].copy()
    raise ValueError(mode)

def disp_steps(f, B, hyps):
    return np.abs(np.diff(f*B/np.asarray(hyps, float)))

f_, B_, z0, z1 = 700.0, 0.12, 0.5, 50.0
print(f'f={f_:.0f} B={B_} 深度范围 [{z0},{z1}] m')
print(f'视差范围 [{f_*B_/z1:.3f}, {f_*B_/z0:.3f}] px（跨 {z1/z0:.0f} 倍）\\n')
print(' 采样方式   D     最大 Δz            视差步长')
for mode in ['depth', 'disparity']:
    for D in [64, 256]:
        h = hypotheses(f_, B_, z0, z1, D, mode)
        dz = np.diff(h); st = disp_steps(f_, B_, h)
        i = int(np.argmax(dz)); j = int(np.argmax(st))
        extra = (f'恒为 {st[0]:.3f} px' if mode == 'disparity'
                 else f'最大 {st.max():.3f} px @ z={h[j+1]:.2f} m')
        print(f' {mode:10s} {D:4d}  {dz.max():.4f} m @ z={h[i]:.1f}m   {extra}')

_h64d = hypotheses(f_, B_, z0, z1, 64, 'depth')
_h64p = hypotheses(f_, B_, z0, z1, 64, 'disparity')
assert disp_steps(f_, B_, _h64d).max() > 100
assert disp_steps(f_, B_, _h64p).max() < 3
print(f'\\n✓ D=64 时深度均匀的近场视差步长 {disp_steps(f_,B_,_h64d).max():.1f} px'
      f' vs 视差均匀恒为 {disp_steps(f_,B_,_h64p)[0]:.3f} px'
      f'（差 {disp_steps(f_,B_,_h64d).max()/disp_steps(f_,B_,_h64p)[0]:.0f} 倍）')
print('  近场等于**完全没采样** —— 一个像素的匹配代价在 100 px 跨度上早就没有相关性了')

print('\\n而视差均匀的「代价」是远场粗，但那是**正确**的取舍：')
print('  z      σ_z (0.5 px 噪声)     视差均匀时的 Δz')
_h = hypotheses(f_, B_, z0, z1, 64, 'disparity')
for z in [1.0, 5.0, 20.0, 50.0]:
    sz = z**2/(f_*B_)*0.5
    k = int(np.argmin(np.abs(_h - z)))
    dz_local = _h[min(k+1, len(_h)-1)] - _h[max(k-1, 0)]
    print(f' {z:5.1f}   {sz:12.4f} m      {dz_local/2:10.4f} m')
print('\\n✓ 采样间隔与测量不确定度 σ_z 同阶 —— 所以「远场粗」匹配了精度本身的分布')
print('  换句话说：在视差上均匀 = 让每个假设承担**相同的信息量**')

print('\\n所需假设数的闭式 D = f·B·(1/zmin - 1/zmax)：')
for ff, BB, a, b in [(700, .12, .5, 50), (700, .12, 1., 20), (1200, .5, 2., 80),
                     (500, 6., 3., 20), (700, .03, .3, 5)]:
    print(f'  f={ff:5.0f} B={BB:4.2f} [{a:4.1f},{b:5.1f}] m -> D = '
          f'{int(np.ceil(ff*BB*(1/a-1/b)))+1:4d}')
assert int(np.ceil(500*6.0*(1/3.0-1/20.0)))+1 == 851
print('\\n✓ 宽基线航拍需要 851 个假设 —— D ∝ B，所以基线越长代价体越大')"""),

md("""## 3 · 光度一致性的三类失效"""),

code("""def cost_curve(sig, center, win, true_d, hyps=HYPS, slant=0.0, noise=0.0, seed=1):
    '''构造「右图」（视差在窗内按 slant 线性变化），返回各假设的 NCC。'''
    r = np.random.default_rng(seed)
    u = np.arange(center - win//2, center + win//2 + 1)
    right = sample(sig, u - (true_d + slant*(u - center))) + r.normal(0, noise, len(u))
    return np.array([ncc(right, sample(sig, u - d)) for d in hyps])

def peak_margin(curve, hyps=HYPS, exclude=3.0):
    '''返回 (峰值, 次峰, 间隔, argmax 位置)。次峰排除主峰 ±exclude 的邻域。'''
    if np.all(np.isnan(curve)):
        return np.nan, np.nan, np.nan, np.nan
    i = int(np.nanargmax(curve)); est = hyps[i]
    m = np.abs(hyps - est) > exclude
    second = float(np.nanmax(curve[m])) if m.any() else np.nan
    return float(curve[i]), second, float(curve[i] - second), float(est)

TRUE_D = 7.0
print('同一真值 7.0 px、窗口 21、噪声 0.01，只换纹理：')
print(' 纹理       梯度能量    峰值      次峰      间隔       argmax 偏差')
for k in ['rich', 'weak', 'flat', 'periodic']:
    sig = make_signal(k, 0)
    c = cost_curve(sig, 2000, 21, TRUE_D, noise=0.01)
    pk, sc, mg, est = peak_margin(c)
    print(f' {k:9s} {np.mean(np.diff(sig)**2):.3e}  {pk:8.4f}  {sc:8.4f}  {mg:8.4f}   '
          f'{est-TRUE_D:+8.3f} px')

_c_rich = peak_margin(cost_curve(make_signal('rich',0), 2000, 21, TRUE_D, noise=0.01))
_c_weak = peak_margin(cost_curve(make_signal('weak',0), 2000, 21, TRUE_D, noise=0.01))
_c_per  = peak_margin(cost_curve(make_signal('periodic',0), 2000, 21, TRUE_D, noise=0.01))
_c_flat = peak_margin(cost_curve(make_signal('flat',0), 2000, 21, TRUE_D, noise=0.01))
assert _c_rich[2] > 0.4, '宽带纹理的间隔应很大'
assert _c_weak[2] < 0.05, '弱纹理的间隔应很小'
assert abs(_c_per[2]) < 1e-3, '周期纹理的间隔应几乎为 0'
assert abs(_c_per[3] - TRUE_D - 16.0) < 0.5, '周期纹理的误差应恰好是一个周期（16 px）'
# 无纹理区的 argmax 是**随机**的 —— 单个种子可能碰巧接近真值（这次就是），
# 所以正确的判据是「跨多个种子它不携带信息」
_flat_err = []
for _s in range(300):
    _cf2 = cost_curve(make_signal('flat', 0), 2000, 21, TRUE_D, noise=0.01, seed=1000+_s)
    if np.all(np.isnan(_cf2)): continue
    _flat_err.append(HYPS[np.nanargmax(_cf2)] - TRUE_D)
_flat_err = np.array(_flat_err)
_uni_std = (HYPS[-1]-HYPS[0])/np.sqrt(12)          # 均匀分布在整个假设范围上的标准差
_hit1 = float(np.mean(np.abs(_flat_err) <= 1.0))
_chance1 = 2*1.0/(HYPS[-1]-HYPS[0])
assert np.sqrt(np.mean(_flat_err**2)) > 10, '无纹理区的 RMS 误差应很大'
assert abs(_flat_err.std()/_uni_std - 1.0) < 0.15, \
    f'argmax 应近似均匀分布在整个假设范围上：std {_flat_err.std():.2f} vs 均匀 {_uni_std:.2f}'
assert _hit1 < 4*_chance1, f'命中率应接近随机基线：{_hit1:.1%} vs {_chance1:.1%}'
print(f'\\n✓ 间隔把三类完美分开：rich {_c_rich[2]:.4f} / weak {_c_weak[2]:.4f} / '
      f'periodic {_c_per[2]:.4f}')
print(f'✓ 而**峰值**分不开：rich {_c_rich[0]:.4f} / weak {_c_weak[0]:.4f} / '
      f'periodic {_c_per[0]:.4f} —— 都是 0.99 以上')
print(f'✓ 周期纹理的误差是 {_c_per[3]-TRUE_D:+.1f} px = 恰好一个周期（16 px）')
print(f'✓ 无纹理区：NCC **不报 nan**，给出 {_c_flat[0]:.4f} 的「相关性」'
      f'和 {_c_flat[3]:+.2f} px 的视差 —— 这次它碰巧接近真值')
print(f'  但跨 300 个种子：RMS 误差 {np.sqrt(np.mean(_flat_err**2)):.2f} px，'
      f'标准差 {_flat_err.std():.2f}')
print(f'  而「均匀分布在整个假设范围 [{HYPS[0]:.0f},{HYPS[-1]:.0f}]」的标准差是 {_uni_std:.2f}'
      f' —— 几乎一样')
print(f'  |误差|<=1 px 的比例 {_hit1:.1%}，随机基线 {_chance1:.1%} —— 基本是碰运气')
print('  ✓ 所以它的输出**不携带任何信息**，而它看起来像一个正常的测量。')
print('    这也说明：这类实验必须跨多个种子看分布，单个种子会骗人（本例就骗了一次）。')"""),

code("""# 三类失效的**签名**不同
print('加噪后的失败率（200 次试验，|误差|>1 px）：')
print(' 纹理       σ=0.01     σ=0.05     σ=0.2      RMS(σ=0.2)')
sig_fail = {}
for k in ['rich', 'weak', 'periodic']:
    sig = make_signal(k, 0)
    row = []
    for ns in [0.01, 0.05, 0.2]:
        errs = []
        for s in range(200):
            c = cost_curve(sig, 2000, 21, TRUE_D, noise=ns, seed=300+s)
            if np.all(np.isnan(c)): continue
            errs.append(HYPS[np.nanargmax(c)] - TRUE_D)
        errs = np.array(errs)
        row.append((float(np.mean(np.abs(errs) > 1.0)), float(np.sqrt(np.mean(errs**2)))))
    sig_fail[k] = row
    print(f' {k:9s} {row[0][0]:8.0%}   {row[1][0]:8.0%}   {row[2][0]:8.0%}   {row[2][1]:8.3f} px')

assert sig_fail['rich'][2][0] < 0.05, '宽带纹理在 σ=0.2 下仍应几乎不失败'
assert sig_fail['weak'][0][0] < 0.1 and sig_fail['weak'][2][0] > 0.5, \\
    '弱纹理应随噪声**渐进**失效'
assert sig_fail['periodic'][0][0] > 0.5, '周期纹理在最小噪声下就应大量失败'
_pr = sig_fail['periodic']
assert abs(_pr[2][0] - _pr[0][0]) < 0.15, '周期纹理的失败率应**与噪声无关**'
print('\\n✓ 三种**机制**：')
print(f'  rich     —— 不失效（σ 涨 20 倍，失败率仍 {sig_fail["rich"][2][0]:.0%}）')
print(f'  weak     —— 随噪声渐进失效（{sig_fail["weak"][0][0]:.0%} -> '
      f'{sig_fail["weak"][2][0]:.0%}）：间隔 0.027 很快被噪声吃掉')
print(f'  periodic —— **与噪声无关**（{_pr[0][0]:.0%} / {_pr[1][0]:.0%} / {_pr[2][0]:.0%}）：'
      f'有多个完全等价的解')
print('\\n「加噪声不改变误差」= 结构性歧义。')
print('  模块 01 第 6 节的共面场景是同一个签名（E 的方向误差在 0.2 与 1.0 px 下都是 3.15°）')"""),

md("""## 4 · 窗口大小：没有通用答案"""),

code("""def failure_rate(kind, win, slant, noise=0.05, trials=100, seed0=200):
    sig = make_signal(kind, 0); bad = 0
    for s in range(trials):
        c = cost_curve(sig, 2000, win, TRUE_D, slant=slant, noise=noise, seed=seed0+s)
        if np.all(np.isnan(c)): bad += 1; continue
        if abs(HYPS[np.nanargmax(c)] - TRUE_D) > 1.0: bad += 1
    return bad/trials

print('每格 = 100 次试验的失败率（|误差|>1 px），噪声 σ=0.05\\n')
TAB = {}
for slant in [0.0, 0.1, 0.3]:
    print(f' --- 视差梯度 slant = {slant} ---')
    print('  窗口     rich       weak     periodic')
    for win in [5, 9, 21, 41]:
        row = [failure_rate(k, win, slant) for k in ['rich', 'weak', 'periodic']]
        TAB[(slant, win)] = row
        print(f'  {win:4d}   {row[0]:7.0%}   {row[1]:8.0%}   {row[2]:9.0%}')
    print()

# 核心矛盾：同一个窗口在一处唯一可用、在另一处唯一不可用
assert TAB[(0.0, 41)][1] < 0.05, 'slant=0 时弱纹理只有 win41 能用'
assert TAB[(0.0, 21)][1] > 0.1, '而 win21 在弱纹理上仍有明显失败率'
assert TAB[(0.1, 41)][0] > 0.9, 'slant=0.1 时宽带纹理用 win41 应几乎全错'
assert TAB[(0.1, 9)][0] < 0.05 and TAB[(0.1, 21)][0] < 0.05, '而 win9/win21 没问题'
print('✓ 两个格子说明问题：')
print(f'  slant=0.0 时弱纹理：win21 失败 {TAB[(0.0,21)][1]:.0%}，'
      f'win41 失败 {TAB[(0.0,41)][1]:.0%} -> **只有大窗口能用**')
print(f'  slant=0.1 时宽带纹理：win9 失败 {TAB[(0.1,9)][0]:.0%}，'
      f'win21 {TAB[(0.1,21)][0]:.0%}，win41 失败 {TAB[(0.1,41)][0]:.0%} -> **大窗口全错**')
print('  同一个窗口尺寸，在一处是唯一可用的、在另一处是唯一不可用的。')
print('  所以「用 k×k 的窗口」这句话本身就不完整 —— 它必须依赖局部内容。')

# 反直觉：倾斜修好了周期纹理
print('\\n⚠ 反直觉的一条：倾斜**修好**了周期纹理')
print('  slant     win21     win41')
for slant in [0.0, 0.1, 0.3]:
    print(f'   {slant:.1f}    {TAB[(slant,21)][2]:7.0%}   {TAB[(slant,41)][2]:7.0%}')
assert TAB[(0.3, 41)][2] < 0.1, 'slant=0.3 + win41 时周期纹理应几乎不失败'
assert TAB[(0.0, 41)][2] > 0.5, '而 slant=0 时它大量失败'
print(f'\\n✓ 周期纹理 + win41：slant=0 时失败 {TAB[(0.0,41)][2]:.0%}，'
      f'slant=0.3 时只有 {TAB[(0.3,41)][2]:.0%}')
print('  原因：窗内视差线性变化时，周期图案不再能在「偏移一个周期」处对齐。')
print('  所以斜面假设（PatchMatch Stereo）不只修好倾斜，还顺带修好一类周期歧义。')"""),

md("""## 5 · 视差梯度与倾角：$\\mathrm dd/\\mathrm du = -(B/z)\\tan\\theta$"""),

code("""def slant_to_angle(s, bz):
    '''视差梯度 s、基线深度比 bz -> 表面倾角（度）。'''
    return float(np.degrees(np.arctan(abs(s)/bz)))

print('同一个视差梯度对应的物理倾角取决于 B/z：\\n')
print(' 视差梯度   B/z=0.05   B/z=0.2   B/z=1.0   B/z=2.0')
for s in [0.05, 0.15, 0.30, 1.00]:
    row = '  '.join(f'{slant_to_angle(s, bz):7.1f}°' for bz in [0.05, 0.2, 1.0, 2.0])
    print(f'  {s:8.2f}   {row}')

assert abs(slant_to_angle(0.30, 0.05) - 80.5) < 0.5
assert abs(slant_to_angle(0.30, 2.0) - 8.5) < 0.5
print(f'\\n✓ 「视差梯度 0.3」这一档（第 4 节里宽带纹理全错的那档）：')
print(f'  窄基线 B/z=0.05 -> {slant_to_angle(0.30,0.05):.1f}°（几乎侧着，很罕见）')
print(f'  宽基线 B/z=2.0  -> {slant_to_angle(0.30,2.0):.1f}°（几乎任何真实表面都超过它）')
print('  所以宽基线的代价不只是代价体变大（第 2 节的 D=851），')
print('  更是**前平行假设几乎必然被破坏**。')

print('\\n|dd/du| = 1 的临界（人类双目融合的视差梯度极限，Burt & Julesz 1980）：')
for bz in [0.05, 0.2, 1.0, 2.0]:
    print(f'  B/z={bz:.2f}: 临界倾角 {slant_to_angle(1.0, bz):.1f}°')
print('  几何含义：表面与两条视线之一平行 —— 此时它在一只眼里被压缩到零宽度。')
print('  所以这不是生理限制，是几何限制：任何立体方法都撞在同一个界上。')

# 把第 2、5 节合起来：宽基线的完整取舍
print('\\n宽基线的完整取舍（f=700, z=10 m, 深度范围 [3,30] m）：')
print(' B(m)   B/z     σ_z(0.5px)   所需 D   倾角 15° 时的视差梯度')
for B in [0.1, 0.5, 2.0, 10.0]:
    bz = B/10.0
    sz = 10.0**2/(700*B)*0.5
    D_ = int(np.ceil(700*B*(1/3.0 - 1/30.0))) + 1
    g = bz*np.tan(np.deg2rad(15.0))
    print(f' {B:5.1f}  {bz:.4f}  {sz:9.4f} m   {D_:6d}   {g:.4f}')
print('\\n✓ B 增大：σ_z ∝ 1/B 变好，但 D ∝ B 变大、视差梯度 ∝ B/z 变大。')
print('  所以实践中用「多组中等基线」而不是「一组大基线」——')
print('  COLMAP 的 pixelwise view selection 就是在做这件事。')"""),

md("""## 6 · 多视角聚合：它修好的不只是噪声"""),

code("""def multiview_cost(sig, center, win, true_d, n_views, noise, seed, agg='mean',
                   n_occl=0, hyps=HYPS):
    '''n_views 个源视图，基线比例在 0.6~1.4 之间。n_occl 个被遮挡（代价是纯噪声）。'''
    r = np.random.default_rng(seed)
    u = np.arange(center - win//2, center + win//2 + 1)
    scales = np.linspace(0.6, 1.4, n_views) if n_views > 1 else np.array([1.0])
    costs = []
    for i, sc in enumerate(scales):
        if i < n_occl:
            src = r.normal(0, 1, len(u))                 # 遮挡：看到的是别的东西
        else:
            src = sample(sig, u - true_d*sc) + r.normal(0, noise, len(u))
        costs.append(np.array([ncc(src, sample(sig, u - d*sc)) for d in hyps]))
    C = np.stack(costs, 0)
    return {'mean': np.nanmean, 'median': np.nanmedian, 'min': np.nanmin}[agg](C, 0)

print('不等基线的多视角聚合（噪声 0.01 看间隔、0.05 看失败率）：\\n')
MV = {}
for k in ['rich', 'weak', 'periodic']:
    sig = make_signal(k, 0)
    print(f' {k}:')
    print('   视图数   峰值      次峰      间隔      失败率(σ=0.05, 100 次)')
    for nv in [1, 2, 4, 8]:
        c = multiview_cost(sig, 2000, 21, TRUE_D, nv, 0.01, 1)
        pk, sc_, mg, est = peak_margin(c)
        bad = 0
        for s in range(100):
            cc = multiview_cost(sig, 2000, 21, TRUE_D, nv, 0.05, 400+s)
            if np.all(np.isnan(cc)): bad += 1; continue
            if abs(HYPS[np.nanargmax(cc)] - TRUE_D) > 1.0: bad += 1
        MV[(k, nv)] = (mg, bad/100)
        print(f'   {nv:5d}   {pk:.4f}  {sc_:.4f}  {mg:.4f}   {bad/100:.0%}')
    print()

assert MV[('periodic', 1)][1] > 0.5, '一个视图时周期纹理应大量失败'
assert MV[('periodic', 2)][1] < 0.1, '**两个**视图就应修好'
assert MV[('periodic', 2)][0] > 0.1, '间隔应从 0 变成可观'
assert MV[('rich', 8)][0] > MV[('rich', 1)][0], '宽带纹理的间隔应单调变好'
assert MV[('weak', 8)][1] < MV[('weak', 1)][1], '弱纹理的失败率应改善'
print(f'✓ 周期纹理：1 视图失败 {MV[("periodic",1)][1]:.0%}（间隔 {MV[("periodic",1)][0]:.4f}）')
print(f'          **2 视图失败 {MV[("periodic",2)][1]:.0%}**（间隔 {MV[("periodic",2)][0]:.4f}）')
print('  原因不是「数据变多」，是**结构性歧义被打破**：')
print('  两个源视图基线不同，所以「偏移一个周期」在它们各自的视差坐标里对应')
print('  **不同**的假设编号 —— 错误峰不重合、真峰重合。')
print('  这是多视图立体优于双目立体的**本质**原因。')

print(f'\\n⚠ 而弱纹理的间隔**没有**单调变好：'
      f'{MV[("weak",1)][0]:.4f}（1 视图）-> {MV[("weak",2)][0]:.4f}（2 视图）'
      f' -> {MV[("weak",8)][0]:.4f}（8 视图）')
print(f'  但失败率从 {MV[("weak",1)][1]:.0%}（1 视图）降到 '
      f'{MV[("weak",2)][1]:.0%}（2 视图）并保持在 0~1%。')
print('  因为聚合同时做了两件事：改变曲线的**形状**（间隔）与降低曲线上的**噪声**。')
print('  对弱纹理，第二件事的收益更大 —— 所以「间隔变小但失败率变好」并不矛盾。')"""),

code("""# 聚合方式：「要求所有视图都同意」最不稳健
print('8 个源视图里有 k 个被遮挡（代价是纯噪声）时的失败率：\\n')
print(' 被遮挡数   均值(mean)   中位数(median)   最小值(min，即「都同意」)')
AGG = {}
sig = make_signal('rich', 0)
for no in [0, 1, 2, 4, 6]:
    row = []
    for agg in ['mean', 'median', 'min']:
        bad = 0
        for s in range(80):
            c = multiview_cost(sig, 2000, 21, TRUE_D, 8, 0.05, 500+s,
                               agg=agg, n_occl=no)
            if np.all(np.isnan(c)): bad += 1; continue
            if abs(HYPS[np.nanargmax(c)] - TRUE_D) > 1.0: bad += 1
        row.append(bad/80)
    AGG[no] = row
    print(f'  {no:6d}     {row[0]:8.0%}     {row[1]:11.0%}     {row[2]:14.0%}')

assert AGG[1][2] > 0.15, 'min 在 1/8 被遮挡时就应明显失败'
assert AGG[2][2] > AGG[1][2], 'min 应随遮挡数单调变差'
assert AGG[4][0] < 0.05, '而 mean 在 4/8 被遮挡时仍应几乎不失败'
assert AGG[4][2] > AGG[4][0], 'min 必须差于 mean'
print(f'\\n✓ 直觉会说「取最小值最保守、最安全」，而实测正相反：')
print(f'  min 在**1/8**被遮挡时就已失败 {AGG[1][2]:.0%}，2/8 时 {AGG[2][2]:.0%}，'
      f'而 mean 在 4/8 时仍是 {AGG[4][0]:.0%}')
print(f'  而 6/8 被遮挡时：mean {AGG[6][0]:.0%} < median {AGG[6][1]:.0%} < min {AGG[6][2]:.0%}'
      f' —— 连中位数都不如均值')
print('  因为 min 完全由**最差**的那个视图决定 —— 一个被遮挡的视图就能把真峰按下去。')
print('  「保守」在这里等于「对离群点零容忍地敏感」。')
print('\\n所以真实的 MVS 不用 min，而是「先**挑**视图，再对挑出的做（稳健）均值」。')"""),

md("""## 7 · 左右一致性：它抓遮挡，抓不到周期结构"""),

code("""def lr_consistency(d_left, d_right, tau=1.0):
    '''左右一致性检验。要求 |d_L(u) - d_R(u - d_L(u))| < tau。
    返回 (通过掩码, 落在图内的掩码)。'''
    d_left = np.asarray(d_left, float); d_right = np.asarray(d_right, float)
    n = len(d_left)
    u = np.arange(n)
    v = u - d_left
    inside = (v >= 0) & (v <= n-1)
    vi = np.clip(v, 0, n-1)
    i0 = np.floor(vi).astype(int); fr = vi - i0
    i1 = np.minimum(i0 + 1, n-1)
    dr = d_right[i0]*(1-fr) + d_right[i1]*fr
    return inside & (np.abs(d_left - dr) < tau), inside

def make_lr_scene(n=400, split=200, d_far=3.0, d_near=8.0):
    '''左半是远处表面、右半是近处表面。返回 (d_left 真值, d_right 真值)。
    d_right 用 z-buffer 构造：视差大（近）的胜出。'''
    u = np.arange(n)
    dL = np.where(u < split, d_far, d_near)
    dR = np.full(n, np.nan)
    for i in range(n):
        j = int(round(i - dL[i]))
        if 0 <= j < n and (np.isnan(dR[j]) or dL[i] > dR[j]):
            dR[j] = dL[i]
    known = np.where(~np.isnan(dR))[0]
    for j in np.where(np.isnan(dR))[0]:
        dR[j] = dR[known[int(np.argmin(np.abs(known - j)))]]
    return dL, dR

N_LR = 400
dL_true, dR_true = make_lr_scene(N_LR)
print(f'场景：左半 {N_LR//2} 个像素是远处表面（d=3），右半是近处表面（d=8）')
print(f'  被遮挡的左像素应当在 u ≈ [{200-8}, {200-1}]（它们在右图里被近处表面挡住）\\n')

print(' 情形                  图内通过率   图内不通过的位置')
CASES = {}
m, ins = lr_consistency(dL_true, dR_true, 1.0)
CASES['正常（真值）'] = (m[ins].mean(), np.where(ins & ~m)[0])
dL_bad = dL_true.copy(); dL_bad[100:120] = 6.0
m2, ins2 = lr_consistency(dL_bad, dR_true, 1.0)
CASES['左图 100:120 估错'] = (m2[ins2].mean(), np.where(ins2 & ~m2)[0])
m3, ins3 = lr_consistency(dL_true + 16.0, dR_true + 16.0, 1.0)
CASES['周期（两侧同错 16 px）'] = (m3[ins3].mean(), np.where(ins3 & ~m3)[0])
for tag, (rate, bad) in CASES.items():
    print(f' {tag:22s} {rate:9.1%}    {bad[:12].tolist()}'
          + (' ...' if len(bad) > 12 else ''))

_r_ok, _b_ok = CASES['正常（真值）']
_r_bad, _b_bad = CASES['左图 100:120 估错']
_r_per, _b_per = CASES['周期（两侧同错 16 px）']
assert 0.95 < _r_ok < 1.0, f'正常情形应有少量（遮挡）不通过，实测 {_r_ok:.1%}'
assert all(190 <= b <= 200 for b in _b_ok), f'不通过的应集中在遮挡区，实测 {_b_ok.tolist()}'
assert set(range(100, 120)).issubset(set(_b_bad.tolist())), '估错的整段都应被检出'
assert _r_bad < _r_ok - 0.03
assert _r_per > 0.95, f'两侧一致地错应仍然「通过」，实测 {_r_per:.1%}'
print(f'\\n✓ 遮挡被精确定位：不通过的是 {_b_ok.tolist()} —— 正是被近处表面挡住的'
      f' {len(_b_ok)} 个左像素')
print(f'✓ 估错的那一段（100:120）被完整检出（通过率 {_r_bad:.1%}）')
print(f'✓ 而周期错误**没有**被检出（通过率 {_r_per:.1%}）——')
print('  因为两次估计**一致地**错到同一个周期上，于是它们互相「验证」了。')
print('\\n所以左右一致性专门抓「对应根本不存在」（遮挡）与「单侧估错」，')
print('  而抓不到「有多个等价对应」（周期结构）。')
print('  后者只能靠：非局部先验（SGM）、斜面假设（第 4 节）、或多视角聚合（第 6 节）。')

print('\\ntau 的作用（左图带 0.8 px 噪声）：')
_dLn = dL_true + np.random.default_rng(0).normal(0, 0.8, N_LR)
for _t in [0.2, 1.0, 3.0, 10.0]:
    _mm, _ii = lr_consistency(_dLn, dR_true, _t)
    print(f'  tau={_t:5.1f}: 图内通过率 {_mm[_ii].mean():6.1%}')
print('  ✓ tau 是「容忍多少估计噪声」与「漏掉多少遮挡」之间的取舍。')
print('    典型取 1 px —— 而它必须大于亚像素插值的精度（0.1~0.25 px）')

print('\\n为什么这一条检验有价值：')
print('  遮挡与弱纹理在代价曲线上都是「平的」（第 3 节），但成因不同 ——')
print('  弱纹理是信息不足（两次估计会**一致地**错），')
print('  遮挡是对应不存在（两次估计**必然**不一致）。')
print('  所以它的价值不是「找出错的像素」，而是**区分错的原因**。')"""),

md("""---
## ✏️ 练习

四道题各自独立。先写 TODO，再跑下一格的自测。"""),

md("""### ✏️ 练习 1 · 构造代价曲线

实现 `my_cost(sig, center, win, true_d, hyps, slant, noise, seed)`：
构造「右图」窗口（视差在窗内按 `slant` 线性变化：$d(u) = d_0 + \\text{slant}\\cdot(u - center)$，
并加噪），然后对每个假设 `d` 取「左图平移 $d$」的窗口，算 NCC。

采样用 `sample`，相关用 `ncc`。"""),

code("""def my_cost(sig, center, win, true_d, hyps=HYPS, slant=0.0, noise=0.0, seed=1):
    '''返回长度 len(hyps) 的 NCC 数组。'''
    # TODO: r = np.random.default_rng(seed)
    #       u = np.arange(center - win//2, center + win//2 + 1)
    #       right = sample(sig, u - (true_d + slant*(u-center))) + r.normal(0, noise, len(u))
    #       返回 np.array([ncc(right, sample(sig, u - d)) for d in hyps])
    raise NotImplementedError"""),

code("""# ---- 自测 1 ----
_sig_r = make_signal('rich', 0)
_sig_p = make_signal('periodic', 0)
_sig_f = make_signal('flat', 0)

# ① 无噪声、无倾斜时，真值处的 NCC 应为 1
_c = my_cost(_sig_r, 2000, 21, 7.0, noise=0.0, slant=0.0)
assert _c.shape == (len(HYPS),), f'形状 {_c.shape}'
_i = int(np.nanargmax(_c))
assert abs(HYPS[_i] - 7.0) < 1e-9, f'argmax 应恰在 7.0，实测 {HYPS[_i]}'
assert _c[_i] > 0.9999, f'真值处 NCC 应≈1，实测 {_c[_i]:.6f}'

# ② 与参考实现逐位一致（同 seed）
for _kw in [dict(), dict(noise=0.05), dict(slant=0.2), dict(slant=0.1, noise=0.03)]:
    _a = my_cost(_sig_r, 2000, 21, 7.0, **_kw, seed=11)
    _b = cost_curve(_sig_r, 2000, 21, 7.0, **_kw, seed=11)
    assert np.allclose(_a, _b, equal_nan=True), f'{_kw} 与参考不符'

# ③ 非整数真值也能被亚像素网格找到
_c2 = my_cost(_sig_r, 2000, 21, 7.25, noise=0.0)
assert abs(HYPS[int(np.nanargmax(_c2))] - 7.25) < 0.26

# ④ 周期纹理：真值处与偏移一个周期处的 NCC 应几乎相同
_cp = my_cost(_sig_p, 2000, 21, 7.0, noise=0.0)
_i7 = int(np.argmin(np.abs(HYPS - 7.0)))
_i23 = int(np.argmin(np.abs(HYPS - 23.0)))
assert abs(_cp[_i7] - _cp[_i23]) < 1e-6, \\
    f'周期 16 -> d=7 与 d=23 应等价：{_cp[_i7]:.6f} vs {_cp[_i23]:.6f}'

# ⑤ 无纹理：曲线**非 nan**（因为信号里有 1e-3 噪声），但输出不携带信息。
#    单个种子可能碰巧接近真值，所以判据必须是跨种子的分布。
#    注意：噪声必须 >0 —— 零噪声时右图是左图的精确副本，任何纹理都能完美匹配。
_cf = my_cost(_sig_f, 2000, 21, 7.0, noise=0.01, seed=1)
assert not np.all(np.isnan(_cf)), '信号里有 1e-3 噪声，所以 NCC 不该全 nan'
assert np.nanmax(_cf) < 0.9, f'无纹理区带噪声时峰值应明显低于 1，实测 {np.nanmax(_cf):.4f}'
_cf0 = my_cost(_sig_f, 2000, 21, 7.0, noise=0.0)
assert np.nanmax(_cf0) > 0.999, '而零噪声时它能完美匹配（右图是精确副本）'
_fe = []
for _s in range(200):
    _c5 = my_cost(_sig_f, 2000, 21, 7.0, noise=0.01, seed=2000+_s)
    if not np.all(np.isnan(_c5)):
        _fe.append(HYPS[int(np.nanargmax(_c5))] - 7.0)
_fe = np.array(_fe)
_uni = (HYPS[-1]-HYPS[0])/np.sqrt(12)
assert np.sqrt(np.mean(_fe**2)) > 10, f'RMS 误差应很大，实测 {np.sqrt(np.mean(_fe**2)):.2f}'
assert abs(_fe.std()/_uni - 1.0) < 0.2, \
    f'argmax 应近似均匀分布在整个假设范围上：std {_fe.std():.2f} vs 均匀 {_uni:.2f}'

# ⑥ 倾斜会降低峰值
_p0 = np.nanmax(my_cost(_sig_r, 2000, 41, 7.0, slant=0.0, noise=0.0))
_p3 = np.nanmax(my_cost(_sig_r, 2000, 41, 7.0, slant=0.3, noise=0.0))
assert _p3 < _p0 - 0.1, f'倾斜应明显降低峰值：{_p0:.4f} -> {_p3:.4f}'
print(f'✓ 练习 1 通过：真值处 NCC {_c[_i]:.6f}；周期纹理 d=7 与 d=23 差 '
      f'{abs(_cp[_i7]-_cp[_i23]):.1e}')
print(f'  无纹理区：带 0.01 噪声时峰值只有 {np.nanmax(_cf):.4f}'
      f'（而零噪声时是 {np.nanmax(_cf0):.4f} —— 精确副本总能匹配）')
print(f'  200 个种子的 argmax 标准差 {_fe.std():.2f}'
      f'（均匀分布在整个假设范围上的理论值 {_uni:.2f}）—— 不携带信息')
print(f'  win41 倾斜后峰值 {_p0:.4f} -> {_p3:.4f}')"""),

md("""### 📖 参考答案 1"""),

code("""def my_cost(sig, center, win, true_d, hyps=HYPS, slant=0.0, noise=0.0, seed=1):
    r = np.random.default_rng(seed)
    u = np.arange(center - win//2, center + win//2 + 1)
    right = sample(sig, u - (true_d + slant*(u - center))) + r.normal(0, noise, len(u))
    return np.array([ncc(right, sample(sig, u - d)) for d in hyps])

print('参考答案 1 已定义')
print('要点一：slant 作用在**构造右图**时，而不是在搜索假设时 ——')
print('       因为「窗内视差恒定」正是 plane sweep 的假设。')
print('       这道题的整个设置就是「真实世界有倾斜，而算法假设没有」。')
print('要点二：自测 ⑤ 是最重要的一档。无纹理区的 NCC **不返回 nan**（因为有微小噪声），')
print('       所以代价函数不会告诉你「我不知道」—— 它给一个看起来正常的数。')
print('       MVS 必须**显式**按梯度能量或峰-次峰间隔剔除这些像素。')
print('要点三：自测 ④ 验证了周期歧义是**精确**的等价（差 1e-6 量级），')
print('       所以它不可能被任何「更好的代价函数」修好 —— 必须引入额外约束。')"""),

md("""### ✏️ 练习 2 · 峰-次峰间隔（置信度）

实现 `my_margin(curve, hyps, exclude)`：返回 `(峰值, 次峰, 间隔, argmax 位置)`。
次峰的定义：排除主峰 $\\pm$`exclude` 邻域之后的最大值。
曲线全为 `nan` 时返回四个 `nan`。"""),

code("""def my_margin(curve, hyps=HYPS, exclude=3.0):
    '''返回 (峰值, 次峰, 间隔, argmax 位置)。'''
    # TODO: 若 np.all(np.isnan(curve)) 返回 (nan, nan, nan, nan)
    #       i = np.nanargmax(curve) ; est = hyps[i]
    #       mask = np.abs(hyps - est) > exclude
    #       second = np.nanmax(curve[mask]) if mask.any() else nan
    #       返回 (curve[i], second, curve[i]-second, est)
    raise NotImplementedError"""),

code("""# ---- 自测 2 ----
# ① 与参考实现一致
for _k in ['rich', 'weak', 'periodic', 'flat']:
    _c = cost_curve(make_signal(_k, 0), 2000, 21, 7.0, noise=0.01)
    _a = my_margin(_c); _b = peak_margin(_c)
    assert all((np.isnan(x) and np.isnan(y)) or abs(x-y) < 1e-12
               for x, y in zip(_a, _b)), f'{_k} 与参考不符'

# ② 间隔把三类分开
_m = {k: my_margin(cost_curve(make_signal(k, 0), 2000, 21, 7.0, noise=0.01))[2]
      for k in ['rich', 'weak', 'periodic']}
assert _m['rich'] > 0.4, f'rich 的间隔应 >0.4，实测 {_m["rich"]:.4f}'
assert _m['weak'] < 0.05, f'weak 的间隔应 <0.05，实测 {_m["weak"]:.4f}'
assert abs(_m['periodic']) < 1e-3, f'periodic 的间隔应≈0，实测 {_m["periodic"]:.6f}'
assert _m['rich'] > 10*_m['weak'], '三类应被清楚分开'

# ③ **峰值**分不开（这是间隔比峰值有用的理由）
_pk = {k: my_margin(cost_curve(make_signal(k, 0), 2000, 21, 7.0, noise=0.01))[0]
       for k in ['rich', 'weak', 'periodic']}
assert all(v > 0.99 for v in _pk.values()), \\
    f'三类的峰值都应 >0.99（所以峰值没有区分力）：{_pk}'

# ④ 全 nan
_nanc = np.full(len(HYPS), np.nan)
assert all(np.isnan(x) for x in my_margin(_nanc))

# ⑤ exclude 的作用与它的边界
_cp = cost_curve(make_signal('periodic', 0), 2000, 21, 7.0, noise=0.0)
# 周期歧义在整个搜索范围内有多个等价峰（d = 7 + 16k -> -25, -9, +7, +23），
# 所以**任何** exclude 都排不掉全部竞争者 —— 间隔恒为 0
_exs = {e: my_margin(_cp, exclude=e)[2] for e in [1.0, 3.0, 8.0, 12.0, 20.0, 25.0]}
for _e, _v in _exs.items():
    assert abs(_v) < 1e-6, f'exclude={_e} 时间隔仍应为 0，实测 {_v:.2e}'
# 而 exclude 真正排掉的是**真峰自己的肩部**（亚像素邻域）
_cr = cost_curve(make_signal('rich', 0), 2000, 21, 7.0, noise=0.0)
_m_ex0 = my_margin(_cr, exclude=0.3)[2]      # 几乎不排除 -> 次峰就是肩部
_m_ex3 = my_margin(_cr, exclude=3.0)[2]
assert _m_ex0 < _m_ex3 * 0.5, \
    f'exclude 太小时次峰是真峰的肩部，间隔被低估：{_m_ex0:.4f} vs {_m_ex3:.4f}'
print(f'✓ 练习 2 通过：间隔 rich {_m["rich"]:.4f} / weak {_m["weak"]:.4f} / '
      f'periodic {_m["periodic"]:.6f}')
print(f'  而峰值都 >0.99（{_pk["rich"]:.4f}/{_pk["weak"]:.4f}/{_pk["periodic"]:.4f}）'
      f' —— 峰值没有区分力')
print(f'  周期歧义：exclude 从 1 到 25 的间隔都是 0 '
      f'（{", ".join(f"{v:.0e}" for v in _exs.values())}）——')
print('  因为等价峰在 d = 7 + 16k 处遍布整个搜索范围，任何排除窗口都排不掉全部竞争者。')
print(f'  而 exclude 真正的作用是排掉**真峰自己的肩部**：'
      f'exclude=0.3 时间隔 {_m_ex0:.4f}，exclude=3 时 {_m_ex3:.4f}')
print('  所以 exclude 取 1~3 px（约等于代价曲线的主峰宽度），而不是「大于可能的歧义间距」。')"""),

md("""### 📖 参考答案 2"""),

code("""def my_margin(curve, hyps=HYPS, exclude=3.0):
    curve = np.asarray(curve, float)
    if np.all(np.isnan(curve)):
        return np.nan, np.nan, np.nan, np.nan
    i = int(np.nanargmax(curve)); est = float(hyps[i])
    mask = np.abs(hyps - est) > exclude
    second = float(np.nanmax(curve[mask])) if mask.any() else np.nan
    return float(curve[i]), second, float(curve[i] - second), est

print('参考答案 2 已定义')
print('要点一：为什么用「间隔」而不是「峰值」当置信度 —— 自测 ③ 说明了：')
print('       三类纹理的峰值都在 0.99 以上，完全没有区分力。')
print('       而间隔把它们分成 0.47 / 0.027 / 0.000 三档。')
print('要点二：exclude 的含义是「排掉真峰自己的肩部」，而不是「排掉竞争者」。')
print('       自测 ⑤ 说明了这一点：周期歧义在整个搜索范围内有多个等价峰，')
print('       所以 exclude 从 1 到 25 的间隔都是 0 —— 排不掉。')
print('       而 exclude 取得太小（0.3）时次峰就是真峰的肩部，间隔被**低估**。')
print('       所以它应当约等于代价曲线主峰的宽度（典型 1~3 px）。')
print('要点三：SGM 与 PatchMatch 类实现输出的「唯一性比」就是这个量的变体')
print('       （通常是 second/peak 而不是 peak-second，两者等价）。')"""),

md("""### ✏️ 练习 3 · 多视角聚合

实现 `my_multiview(sig, center, win, true_d, n_views, noise, seed, agg, n_occl)`：
`n_views` 个源视图，第 $i$ 个的基线比例是 `np.linspace(0.6, 1.4, n_views)[i]`
（所以它看到的视差是 `true_d * scale`）；前 `n_occl` 个被遮挡（源窗口是纯噪声）。
`agg ∈ {'mean','median','min'}`，用对应的 `np.nan*` 函数沿视图维聚合。"""),

code("""def my_multiview(sig, center, win, true_d, n_views, noise, seed,
                 agg='mean', n_occl=0, hyps=HYPS):
    '''返回聚合后的代价曲线。'''
    # TODO: r = np.random.default_rng(seed)
    #       u = np.arange(center-win//2, center+win//2+1)
    #       scales = np.linspace(0.6,1.4,n_views) if n_views>1 else np.array([1.0])
    #       对每个 i, sc：
    #          i < n_occl -> src = r.normal(0,1,len(u))
    #          否则       -> src = sample(sig, u - true_d*sc) + r.normal(0,noise,len(u))
    #          cost_i = [ncc(src, sample(sig, u - d*sc)) for d in hyps]   ← 注意 d*sc
    #       堆成 (n_views, len(hyps))，再按 agg 用 nanmean/nanmedian/nanmin 沿 axis=0
    raise NotImplementedError"""),

code("""# ---- 自测 3 ----
_sr = make_signal('rich', 0); _sp = make_signal('periodic', 0)

# ① 与参考实现一致
for _nv in [1, 2, 4, 8]:
    for _ag in ['mean', 'median', 'min']:
        _a = my_multiview(_sr, 2000, 21, 7.0, _nv, 0.02, 7, agg=_ag)
        _b = multiview_cost(_sr, 2000, 21, 7.0, _nv, 0.02, 7, agg=_ag)
        assert np.allclose(_a, _b, equal_nan=True), f'nv={_nv} agg={_ag} 与参考不符'

# ② 单视图 + mean 应等于普通 NCC 曲线的形状（argmax 在真值）
_c1 = my_multiview(_sr, 2000, 21, 7.0, 1, 0.0, 3)
assert abs(HYPS[int(np.nanargmax(_c1))] - 7.0) < 0.26

# ③ **关键**：周期纹理 1 视图有歧义、2 视图没有
_p1 = my_multiview(_sp, 2000, 21, 7.0, 1, 0.01, 5)
_p2 = my_multiview(_sp, 2000, 21, 7.0, 2, 0.01, 5)
_mg1 = my_margin(_p1)[2]; _mg2 = my_margin(_p2)[2]
assert abs(_mg1) < 1e-3, f'1 视图时间隔应≈0，实测 {_mg1:.6f}'
assert _mg2 > 0.1, f'2 视图时间隔应 >0.1，实测 {_mg2:.4f}'
# 失败率
def _fail(nv, ntr=60):
    bad = 0
    for s in range(ntr):
        c = my_multiview(_sp, 2000, 21, 7.0, nv, 0.05, 600+s)
        if np.all(np.isnan(c)): bad += 1; continue
        if abs(HYPS[np.nanargmax(c)] - 7.0) > 1.0: bad += 1
    return bad/ntr
_f1, _f2 = _fail(1), _fail(2)
assert _f1 > 0.5 and _f2 < 0.15, f'周期纹理：1 视图 {_f1:.0%} -> 2 视图 {_f2:.0%}'

# ④ 宽带纹理的间隔随视图数单调变好
_mgs = [my_margin(my_multiview(_sr, 2000, 21, 7.0, nv, 0.01, 1))[2] for nv in [1, 2, 4, 8]]
assert all(_mgs[i] < _mgs[i+1] for i in range(3)), f'应单调，实测 {_mgs}'

# ⑤ min 对遮挡最不稳健
def _fail_agg(agg, no, ntr=60):
    bad = 0
    for s in range(ntr):
        c = my_multiview(_sr, 2000, 21, 7.0, 8, 0.05, 700+s, agg=agg, n_occl=no)
        if np.all(np.isnan(c)): bad += 1; continue
        if abs(HYPS[np.nanargmax(c)] - 7.0) > 1.0: bad += 1
    return bad/ntr
_fm, _fmin = _fail_agg('mean', 4), _fail_agg('min', 4)
assert _fmin > _fm, f'min 必须差于 mean：{_fmin:.0%} vs {_fm:.0%}'
assert _fm < 0.1, f'mean 在 4/8 被遮挡时应仍稳健，实测 {_fm:.0%}'
print(f'✓ 练习 3 通过：周期纹理 1 视图失败 {_f1:.0%}（间隔 {_mg1:.6f}）'
      f' -> 2 视图 {_f2:.0%}（间隔 {_mg2:.4f}）')
print(f'  宽带纹理的间隔单调：{[f"{v:.3f}" for v in _mgs]}')
print(f'  4/8 被遮挡时 mean {_fm:.0%} vs min {_fmin:.0%}')"""),

md("""### 📖 参考答案 3"""),

code("""def my_multiview(sig, center, win, true_d, n_views, noise, seed,
                 agg='mean', n_occl=0, hyps=HYPS):
    r = np.random.default_rng(seed)
    u = np.arange(center - win//2, center + win//2 + 1)
    scales = np.linspace(0.6, 1.4, n_views) if n_views > 1 else np.array([1.0])
    costs = []
    for i, sc in enumerate(scales):
        if i < n_occl:
            src = r.normal(0, 1, len(u))
        else:
            src = sample(sig, u - true_d*sc) + r.normal(0, noise, len(u))
        costs.append(np.array([ncc(src, sample(sig, u - d*sc)) for d in hyps]))
    C = np.stack(costs, 0)
    return {'mean': np.nanmean, 'median': np.nanmedian, 'min': np.nanmin}[agg](C, 0)

print('参考答案 3 已定义')
print('要点一：`d*sc` 是这道题的核心。每个源视图的基线不同，所以同一个 3D 深度')
print('       在它那里对应不同的视差。忘了乘 sc 的话，所有视图的错误峰会重合，')
print('       于是自测 ③（周期纹理被 2 视图修好）会失败 ——')
print('       而这恰好证明了「不等基线」才是修好周期歧义的机制。')
print('要点二：min 的失败（自测 ⑤）与直觉相反。「要求所有视图都同意」听起来保守，')
print('       但它完全由最差的那个视图决定，所以对遮挡零容忍地敏感。')
print('要点三：真实实现（COLMAP 的 pixelwise view selection）先**挑**视图再求均值，')
print('       挑的判据同时含基线角度（模块 02 第 5 节）与光度一致性（第 3 节）。')"""),

md("""### ✏️ 练习 4 · 左右一致性检验

实现 `my_lr_check(d_left, d_right, tau)`：返回 `(通过掩码, 图内掩码)`。
判据：$\\vert d_L(u) - d_R(u - d_L(u))\\vert < \\tau$，
其中 $d_R$ 在非整数位置用线性插值；$u - d_L(u)$ 落在图外的像素判为**不通过**
（但要在第二个返回值里标出来，以便与「不一致」分开统计）。"""),

code("""def my_lr_check(d_left, d_right, tau=1.0):
    '''返回 (通过掩码, 图内掩码)，长度都与 d_left 相同。'''
    # TODO: n = len(d_left); u = np.arange(n); v = u - d_left
    #       inside = (v >= 0) & (v <= n-1)
    #       vi = clip(v, 0, n-1); i0 = floor(vi); fr = vi - i0; i1 = min(i0+1, n-1)
    #       dr = d_right[i0]*(1-fr) + d_right[i1]*fr
    #       返回 (inside & (|d_left - dr| < tau), inside)
    raise NotImplementedError"""),

code("""# ---- 自测 4 ----
_dL, _dR = make_lr_scene(400, 200)

# ① 与参考实现一致
for _tau in [0.5, 1.0, 2.0]:
    _a = my_lr_check(_dL, _dR, _tau); _b = lr_consistency(_dL, _dR, _tau)
    assert np.array_equal(_a[0], _b[0]) and np.array_equal(_a[1], _b[1])

# ② 正常情形：只有被遮挡的少数像素不通过，且位置正确
_m, _ins = my_lr_check(_dL, _dR, 1.0)
assert _ins.sum() > 380, '绝大多数像素应落在图内'
_bad = np.where(_ins & ~_m)[0]
assert 3 <= len(_bad) <= 12, f'遮挡区应只有几个像素，实测 {len(_bad)}'
assert all(190 <= b <= 200 for b in _bad), f'位置应在遮挡区，实测 {_bad.tolist()}'

# ③ 单侧估错的整段被检出
_dLb = _dL.copy(); _dLb[100:120] = 6.0
_m2, _i2 = my_lr_check(_dLb, _dR, 1.0)
assert set(range(100, 120)).issubset(set(np.where(_i2 & ~_m2)[0].tolist()))

# ④ 周期错误（两侧一致地错）**通不过检测**
_m3, _i3 = my_lr_check(_dL + 16.0, _dR + 16.0, 1.0)
assert _m3[_i3].mean() > 0.95, f'两侧同错应仍「通过」，实测 {_m3[_i3].mean():.1%}'

# ⑤ 落在图外：两个掩码都应为 False
_dbig = np.full(400, 500.0)
_m4, _i4 = my_lr_check(_dbig, _dR, 1.0)
assert not _m4.any() and not _i4.any(), '全部出图时两个掩码都应全 False'
_dpart = np.where(np.arange(400) < 20, 100.0, 3.0)
_m5, _i5 = my_lr_check(_dpart, _dR, 1.0)
assert not _i5[:20].any() and _i5[20:].all(), '图内掩码应精确标出哪些出图了'

# ⑥ tau 越大越宽松（在图内像素上）
_dn = _dL + np.random.default_rng(0).normal(0, 0.8, 400)
_rates = []
for _t in [0.2, 1.0, 5.0]:
    _mm, _ii = my_lr_check(_dn, _dR, _t)
    _rates.append(_mm[_ii].mean())
assert _rates[0] < _rates[1] < _rates[2], f'应单调，实测 {_rates}'
print(f'✓ 练习 4 通过：正常情形不通过的是 {_bad.tolist()}（遮挡区）；'
      f'估错的整段被检出；周期两侧同错的通过率 {_m3[_i3].mean():.1%}')
print(f'  出图检测正确；tau 0.2/1.0/5.0 的图内通过率 '
      f'{_rates[0]:.1%}/{_rates[1]:.1%}/{_rates[2]:.1%}')"""),

md("""### 📖 参考答案 4"""),

code("""def my_lr_check(d_left, d_right, tau=1.0):
    d_left = np.asarray(d_left, float); d_right = np.asarray(d_right, float)
    n = len(d_left)
    u = np.arange(n)
    v = u - d_left
    inside = (v >= 0) & (v <= n-1)
    vi = np.clip(v, 0, n-1)
    i0 = np.floor(vi).astype(int); fr = vi - i0
    i1 = np.minimum(i0 + 1, n-1)
    dr = d_right[i0]*(1-fr) + d_right[i1]*fr
    return inside & (np.abs(d_left - dr) < tau), inside

print('参考答案 4 已定义')
print('要点一：为什么要返回两个掩码。「出图」与「不一致」是两种不同的失败，')
print('       混在一起统计会让「通过率」变成一个说不清含义的数 ——')
print('       第 7 节里周期那一档如果不分开，通过率会从 96% 掉到 82%，')
print('       而那 14 个百分点全是「出图」而不是「检出了周期错误」。')
print('要点二：自测 ④ 是这道题的重点 —— 周期错误**通不过检测**。')
print('       两次估计一致地错到同一个周期上，于是它们互相「验证」了。')
print('       所以这条检验只能抓「对应不存在」（遮挡）与「单侧估错」。')
print('要点三：它能把遮挡与弱纹理分开 —— 两者的代价曲线都是平的，')
print('       但弱纹理会一致地错、遮挡必然不一致。')
print('       所以它的价值是**区分错的原因**，而不只是找出错的像素。')"""),

md("""---
## 🧪 真实工程胶囊

```python
# ---- COLMAP 的 MVS（PatchMatch，斜面假设）----
colmap patch_match_stereo --workspace_path dense/ \
    --PatchMatchStereo.depth_min 0.5 --PatchMatchStereo.depth_max 50 \
    --PatchMatchStereo.window_radius 5      \
    --PatchMatchStereo.num_samples 15       \
    --PatchMatchStereo.geom_consistency true   # ← 第 7 节的一致性检验（多视角版）
colmap stereo_fusion --workspace_path dense/ --output_path dense/fused.ply \
    --StereoFusion.min_num_pixels 5         # 至少几个视角同意才保留
# depth_min/max 就是练习中的 zmin/zmax —— 而它们决定了所需的假设数（第 2 节的闭式）
# PatchMatch 用**随机化传播**搜索 3 维假设（深度 + 两个梯度），所以不需要显式代价体

# ---- OpenCV 的 SGM（固定窗口 + 非局部路径代价）----
import cv2
sgm = cv2.StereoSGBM_create(
    minDisparity=0, numDisparities=16*10,     # ← 必须是 16 的倍数；对应第 2 节的 D
    blockSize=5,                              # ← 第 4 节的窗口，没有通用答案
    P1=8*3*5**2, P2=32*3*5**2,                # 路径代价的平滑项（第 7 节说的非局部先验）
    uniquenessRatio=10,                       # ← 第 3 节的峰-次峰间隔（百分比形式）
    speckleWindowSize=100, speckleRange=2,
    disp12MaxDiff=1,                          # ← 练习 4 的 tau
    mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY)
disp = sgm.compute(left, right).astype(np.float32)/16.0   # 输出是 1/16 px 定点
# 注意 uniquenessRatio 与 disp12MaxDiff 正是本模块第 3、7 节那两个判据

# ---- 深度学习 MVS（对照）----
# pip install "mvsnet"  /  或用 openMVS、MVSFormer、VisMVSNet
# 它们把「代价体 + 聚合」换成 3D CNN，但**深度假设的采样方式不变** ——
# 所以第 2 节的「必须在视差（逆深度）上均匀」对它们同样成立
# （很多实现里叫 inverse depth sampling）
```

**排查清单**

| 症状 | 先查什么 | 依据 |
|---|---|---|
| 近处的深度全是噪声 | 深度假设是否在视差上均匀 | 深度均匀时近场步长 102.7 px |
| 深度图有明显阶梯 | 有没有亚像素插值 | WTA 只给整数级视差 |
| 大片区域深度乱跳 | 置信度阈值太松 | 无纹理区 NCC **不报错**，给的是噪声 |
| 栅栏/砖墙/键盘处系统性错位 | 周期结构 | 误差恰好一个周期，且**与噪声无关** |
| 物体边缘有错误的「拖尾」 | 左右一致性检验 | 遮挡区两次估计必然不一致 |
| 斜面（地面、屋顶）深度差 | 窗口太大 / 需要斜面假设 | slant=0.1 时 win41 失败 100% |
| 换宽基线后反而更差 | 前平行假设被破坏 | B/z=2 时 8.5° 的倾斜就给出 0.3 的视差梯度 |
| 有几个视角被遮挡就崩 | 聚合方式是不是 min | min 在 2/8 被遮挡时已失败 28% |"""),
]
