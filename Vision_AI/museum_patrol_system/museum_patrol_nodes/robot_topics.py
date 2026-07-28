"""T1 / Gen.G topic paths aligned with URHYNIX team namespaces."""

ROBOT_NS_T1 = 'tb3_1'
ROBOT_NS_GENG = 'tb3_2'


def t1_color_raw(ns: str = ROBOT_NS_T1) -> str:
    return f'/{ns}/camera/color/image_raw'


def t1_color_compressed(ns: str = ROBOT_NS_T1) -> str:
    return f'/{ns}/camera/color/image_raw/compressed'


def geng_image_raw(ns: str = ROBOT_NS_GENG) -> str:
    return f'/{ns}/camera/image_raw'
