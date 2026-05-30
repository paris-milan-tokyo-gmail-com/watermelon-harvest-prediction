import requests
from bs4 import BeautifulSoup
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}


def _fetch_html(url: str) -> BeautifulSoup:
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.encoding = "utf-8"
    return BeautifulSoup(resp.text, "lxml")


def _is_amedas(block_no: str) -> bool:
    """AMeDAS局かどうか判定（官署は47xxxの5桁、AMeDASは0xxxの4桁等）。"""
    return not block_no.startswith("47") or len(block_no) != 5


def get_daily_temps(prec_no: str, block_no: str, year: int, month: int) -> dict[int, float | None]:
    """実測日別平均気温を返す {日: 気温}。欠測は None。"""
    if _is_amedas(block_no):
        # AMeDAS: daily_a1.php, 気温平均は index 4
        view = "daily_a1"
        temp_idx = 4
    else:
        # 官署: daily_s1.php, 気温平均は index 6
        view = "daily_s1"
        temp_idx = 6

    url = (
        f"https://www.data.jma.go.jp/stats/etrn/view/{view}.php"
        f"?prec_no={prec_no}&block_no={block_no}&year={year}&month={month}&day=&view="
    )
    soup = _fetch_html(url)
    table = soup.find("table", id="tablefix1")
    if table is None:
        return {}

    result: dict[int, float | None] = {}
    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if not cells:
            continue
        day_text = cells[0].get_text(strip=True)
        if not re.match(r"^\d+$", day_text):
            continue
        day = int(day_text)
        if len(cells) > temp_idx:
            temp_text = cells[temp_idx].get_text(strip=True)
            try:
                result[day] = float(temp_text)
            except ValueError:
                result[day] = None
    return result


def get_normal_temps(prec_no: str, block_no: str, month: int) -> dict[int, float | None]:
    """平年値日別平均気温を返す {日: 気温}。欠測は None。"""
    if _is_amedas(block_no):
        view = "nml_amd_d"
    else:
        view = "nml_sfc_d"

    url = (
        f"https://www.data.jma.go.jp/stats/etrn/view/{view}.php"
        f"?prec_no={prec_no}&block_no={block_no}&year=&month={month}&day=&view="
    )
    soup = _fetch_html(url)
    table = soup.find("table", id="tablefix1")
    if table is None:
        return {}

    result: dict[int, float | None] = {}
    for row in table.find_all("tr"):
        th = row.find("th")
        if th is None:
            continue
        day_match = re.match(r"^(\d+)日$", th.get_text(strip=True))
        if not day_match:
            continue
        day = int(day_match.group(1))
        cells = row.find_all("td")
        # 官署・AMeDAS共通: 降水量, 平均気温, ...
        if len(cells) > 1:
            temp_text = cells[1].get_text(strip=True)
            try:
                result[day] = float(temp_text)
            except ValueError:
                result[day] = None
    return result
