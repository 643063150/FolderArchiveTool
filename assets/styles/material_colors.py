"""
Material Design 3 (Material You) 配色系统
基于 MD3 规范: https://m3.material.io/styles/color/overview
使用 Tonal Palette (色调调色板) 体系

颜色角色 (Color Roles):
- Primary: 主品牌色，用于主要按钮、导航、关键元素
- Secondary: 次色，用于浮动按钮、选择控件
- Tertiary: 第三色，用于强调、对比
- Neutral: 中性色，用于表面、文字
- Error: 错误色
"""

from dataclasses import dataclass


@dataclass
class TonalPalette:
    """MD3 色调调色板 - 从 0(黑) 到 100(白) 的色调阶"""
    primary: dict
    secondary: dict
    tertiary: dict
    neutral: dict
    error: dict


# ── Material You 种子颜色生成的色调调色板 ──────────────
# 主色种子: #1976D2 (Blue)
# 基于 HCT 颜色空间的 MD3 标准色调阶

PALETTE = TonalPalette(
    primary={
        0: "#000000",
        10: "#001A40",
        20: "#002D6E",
        25: "#003784",
        30: "#00419A",
        35: "#004CB1",
        40: "#1565C0",
        50: "#3B82D6",
        60: "#5B9EEE",
        70: "#85B4F5",
        80: "#A9CBFA",
        90: "#D3E3FD",
        95: "#E8F0FE",
        98: "#F4F8FF",
        99: "#FBFCFF",
        100: "#FFFFFF",
    },
    secondary={
        0: "#000000",
        10: "#0D1B2A",
        20: "#1E3345",
        25: "#294052",
        30: "#344D60",
        35: "#405A6D",
        40: "#4C687B",   # Secondary
        50: "#648194",
        60: "#7D9BAD",
        70: "#97B4C6",
        80: "#B2CEDF",
        90: "#D7E7F0",
        95: "#EBF3F7",
        98: "#F5F9FB",
        99: "#FBFDFE",
        100: "#FFFFFF",
    },
    tertiary={
        0: "#000000",
        10: "#2A0C2E",
        20: "#422345",
        25: "#4F2E52",
        30: "#5C395F",
        35: "#69446C",
        40: "#77507A",   # Tertiary
        50: "#916893",
        60: "#AB81AD",
        70: "#C59BC7",
        80: "#E0B5E1",
        90: "#F2D9F1",
        95: "#F8ECF8",
        98: "#FCF5FC",
        99: "#FEFCFE",
        100: "#FFFFFF",
    },
    neutral={
        0: "#000000",
        4: "#0A0B0D",
        6: "#101317",
        10: "#1A1C1E",
        12: "#1E2124",
        17: "#282A2D",
        20: "#2F3134",
        22: "#343639",
        24: "#383B3E",
        25: "#3B3E41",
        30: "#46474A",
        35: "#515255",
        40: "#5D5E61",
        50: "#76777A",
        60: "#909194",
        70: "#ABABAD",
        80: "#C7C7C9",
        87: "#DADADB",
        90: "#E3E3E4",
        92: "#E9E9EA",
        94: "#EEEEEF",
        95: "#F1F1F2",
        96: "#F4F4F5",
        98: "#F9F9FA",
        99: "#FCFCFD",
        100: "#FFFFFF",
    },
    error={
        0: "#000000",
        10: "#410002",
        20: "#690005",
        25: "#7E0007",
        30: "#93000A",
        35: "#A8000D",
        40: "#BA1A1A",
        50: "#DE3730",
        60: "#FF5449",
        70: "#FF897D",
        80: "#FFB4AB",
        90: "#FFDAD6",
        95: "#FFEDEA",
        98: "#FFF8F7",
        99: "#FFFBFF",
        100: "#FFFFFF",
    },
)


class MD3ColorRoles:
    """
    MD3 颜色角色系统
    每个角色定义了颜色及其"on"色（该颜色上的文字/图标色）
    """

    def __init__(self, variant: str = "light"):
        self.variant = variant
        self._build_roles()

    def _build_roles(self):
        p = PALETTE.primary
        s = PALETTE.secondary
        t = PALETTE.tertiary
        n = PALETTE.neutral
        e = PALETTE.error

        if self.variant == "light":
            # ── 主色 ──
            self.primary = p[40]
            self.on_primary = p[100]
            self.primary_container = p[90]
            self.on_primary_container = p[10]
            self.primary_fixed = p[90]
            self.primary_fixed_dim = p[80]
            self.on_primary_fixed = p[10]
            self.on_primary_fixed_variant = p[30]

            # ── 次色 ──
            self.secondary = s[40]
            self.on_secondary = s[100]
            self.secondary_container = s[90]
            self.on_secondary_container = s[10]

            # ── 第三色 ──
            self.tertiary = t[40]
            self.on_tertiary = t[100]
            self.tertiary_container = t[90]
            self.on_tertiary_container = t[10]

            # ── 错误色 ──
            self.error = e[40]
            self.on_error = e[100]
            self.error_container = e[90]
            self.on_error_container = e[10]

            # ── 背景/表面 ──
            self.background = n[99]
            self.on_background = n[10]
            self.surface = n[99]
            self.on_surface = n[10]
            self.surface_variant = n[90]
            self.on_surface_variant = n[30]
            self.surface_dim = n[87]
            self.surface_bright = n[98]
            self.surface_container_lowest = n[100]
            self.surface_container_low = n[96]
            self.surface_container = n[94]
            self.surface_container_high = n[92]
            self.surface_container_highest = n[90]

            # ── 边框/轮廓 ──
            self.outline = n[60]
            self.outline_variant = n[80]

            # ── 其他 ──
            self.inverse_surface = n[20]
            self.inverse_on_surface = n[95]
            self.inverse_primary = p[80]
            self.scrim = n[0]
            self.shadow = n[0]

        else:  # dark variant
            # ── 主色（深色反转）──
            self.primary = p[80]
            self.on_primary = p[20]
            self.primary_container = p[30]
            self.on_primary_container = p[90]
            self.primary_fixed = p[90]
            self.primary_fixed_dim = p[80]
            self.on_primary_fixed = p[10]
            self.on_primary_fixed_variant = p[30]

            self.secondary = s[80]
            self.on_secondary = s[20]
            self.secondary_container = s[30]
            self.on_secondary_container = s[90]

            self.tertiary = t[80]
            self.on_tertiary = t[20]
            self.tertiary_container = t[30]
            self.on_tertiary_container = t[90]

            self.error = e[80]
            self.on_error = e[20]
            self.error_container = e[30]
            self.on_error_container = e[90]

            self.background = n[10]
            self.on_background = n[90]
            self.surface = n[10]
            self.on_surface = n[90]
            self.surface_variant = n[30]
            self.on_surface_variant = n[80]
            self.surface_dim = n[6]
            self.surface_bright = n[24]
            self.surface_container_lowest = n[4]
            self.surface_container_low = n[10]
            self.surface_container = n[12]
            self.surface_container_high = n[17]
            self.surface_container_highest = n[22]

            self.outline = n[60]
            self.outline_variant = n[30]

            self.inverse_surface = n[90]
            self.inverse_on_surface = n[20]
            self.inverse_primary = p[40]
            self.scrim = n[0]
            self.shadow = n[0]

        # 暴露完整色调调色板（用于需要精确色调的场景，如日志区深色背景）
        self.neutral = PALETTE.neutral
        self.primary_palette = PALETTE.primary
        self.secondary_palette = PALETTE.secondary
        self.tertiary_palette = PALETTE.tertiary
        self.error_palette = PALETTE.error


# ── 便捷访问 ──────────────────────────────────────────

def get_colors(variant: str = "light") -> MD3ColorRoles:
    """获取指定主题的完整颜色角色集"""
    return MD3ColorRoles(variant)


# 默认实例
Colors = get_colors("light")
