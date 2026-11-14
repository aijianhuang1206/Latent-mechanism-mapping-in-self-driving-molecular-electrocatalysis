"""统一比较Step5中的Ep和三组Epp；Arial居中、白底、常规字重的实心圆表。

脚本放入包含下列图片的Step5_comparison文件夹运行：
Ep / Ep-10 fold；Epp-5% / Epp-5% CO2-10 fold；
Epp-100% / Epp-100% CO2-10 fold；Epp-difference / Epp-difference-10 fold。
支持PNG/JPG/JPEG/TIF/TIFF/BMP，不需要在文件名变量里写扩展名。

Epp：红正蓝负，直接比较7×7下三角单元格填充色。
Ep：旧变换sign(Eprime)*log10(abs(Eprime))不保留物理符号；默认自动在脚本
所在目录或上一级的Trial-1...Trial-10/Step5中查找modified_table_scaled.csv。
找不到时记录Ep缺少原始数据，继续完成其他三组，不输出伪物理符号一致率。
5%对应0.0115M，100%对应0.23M；参考Ep物理符号在设置区明确给出。

依赖numpy、pandas、matplotlib、Pillow、scipy。默认只保存文件，不弹出绘图窗口。
"""

from pathlib import Path
import argparse
import csv
from datetime import datetime
import html
import json
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import pandas as pd


# ======================== 设置 ========================
ROOT_DIR = Path(__file__).resolve().parent
OUTPUT_FOLDER = "Step5_sign_comparison_results"
USE_RUN_SUBFOLDERS = True  # 每次运行独立保存，避免缺失组误用上次的旧结果。
SAME_COLOR = "#EF949E"       # 实心粉红色：同号
DIFFERENT_COLOR = "#00B0F0"  # 实心蓝色：异号
UNKNOWN_COLOR = "#B5BDC6"    # 无法可靠判断：不计入有效分母
FONT_SIZE = 14
DOT_SIZE = 130
DOT_EDGE_COLOR = "black"
DOT_EDGE_WIDTH = 0.8
FIGURE_WIDTH_IN = 15.0
ROW_HEIGHT_IN = 0.34
ADD_OVERALL_ROW = True
# 系统Arial默认自动识别；也可填Arial .ttf/.otf文件路径。不会静默替换为其他字体。
ARIAL_FONT_PATH = None
SAVE_DPI = 300
TRIAL_NUMBERS = list(range(1, 11))
RASTER_EXTENSIONS = [".png", ".tif", ".tiff", ".jpg", ".jpeg", ".bmp"]

FEATURES = [
    (5, "TFE"),
    (10, "1,1,1,3,3,3-Hexafluoro-2-methyl-2-propanol"),
    (11, "Phenol"),
    (32, "TBAPF6"),
    (33, "TMAPF6"),
    (34, "CsPF6"),
    (41, "Perylene"),
]
PAIRS = [(a[0], b[0]) for i, a in enumerate(FEATURES) for b in FEATURES[:i+1]]
EPP_CASES = [
    ("Epp_5pct", "Epp-5%", "Epp-5% CO2-10 fold"),
    ("Epp_100pct", "Epp-100%", "Epp-100% CO2-10 fold"),
    ("Epp_difference", "Epp-difference", "Epp-difference-10 fold"),
]

# Ep原始数据目录。None表示依次尝试当前目录和上一级目录。
# 比较文件夹与Trial文件夹为同级时，不必修改这里。
EP_RAW_ROOT = None
SOURCE_FILE = "modified_table_scaled.csv"
CO2_MAX_M = 0.23
R, T = 8.314, 298.15
# 沿用原连续曲线脚本的kobs模型（包含+1000），不混用旧点值脚本的常数。
KOBS_K0, KOBS_KMAX, KOBS_K = 1000.0, 5.24e4, 9.80
ZERO_TOLERANCE = 0.0
EP_FEATURES = [(i,n,"") for i,n in FEATURES]
REFERENCE_SIGNS = {i: (1 if i in (5,33) else -1) for i,_ in FEATURES}
EP_REFERENCE_SIGNS = {5: REFERENCE_SIGNS.copy(), 100: REFERENCE_SIGNS.copy()}
CONDITIONS = [(5,0.05),(100,1.0)]


def normalized_stem(name):
    return re.sub(r"[\s_\-–—]+", "", name.casefold().replace("₂","2"))


def find_picture(root, stem):
    matches = [p for p in root.iterdir() if p.is_file()
               and p.suffix.lower() in RASTER_EXTENSIONS
               and normalized_stem(p.stem) == normalized_stem(stem)]
    if not matches:
        raise FileNotFoundError(f"Missing image: {stem} (PNG/JPG/TIF etc.) in {root}")
    matches.sort(key=lambda p: RASTER_EXTENSIONS.index(p.suffix.lower()))
    return matches[0]


def image_pair_signs(reference_path, trials_path):
    reference_cells, _ = image_cells(reference_path,28)
    trial_cells,(height,width) = image_cells(trials_path,280)
    positions = [(r,c) for r in range(3) for c in range(3)] + [(3,1)]
    panels = {position:[] for position in positions}
    for cell in trial_cells:
        position = (int((cell["y"]+cell["h"]/2)*4/height),
                    int((cell["x"]+cell["w"]/2)*3/width))
        if position not in panels:
            raise ValueError(f"Unexpected matrix cell outside 10-fold panels: {position}")
        panels[position].append(cell)
    reference = cells_to_pairs(reference_cells)
    trials = {i+1:cells_to_pairs(panels[position]) for i,position in enumerate(positions)}
    audit = {"reference_file":str(reference_path),"trial_file":str(trials_path),
             "reference_cells":reference_cells,"trial_cells":trial_cells}
    return reference,trials,audit


def make_rows(reference,trials,terms):
    rows=[]
    for term in terms:
        ref=reference[term]
        signs=[trials[t][term] for t in TRIAL_NUMBERS]
        match=[int(s==ref) if s!=0 and ref!=0 else None for s in signs]
        valid=sum(s is not None for s in match)
        same=sum(s==1 for s in match)
        label=f"{term[0]}, {term[1]}" if isinstance(term,tuple) else str(term)
        rows.append({"term":label,"reference_sign":ref,"trial_signs":signs,
                     "matches":match,"same_count":same,"valid_count":valid,
                     "same_percent":100*same/valid if valid else None})
    return rows


def configure_arial():
    """使用真正的Arial；缺少时明确提示，不再回退到DejaVu Sans。"""
    local_candidates = ([Path(ARIAL_FONT_PATH)] if ARIAL_FONT_PATH is not None
                        else [Path(__file__).resolve().parent/"fonts"/"arial.ttf"])
    for candidate in local_candidates:
        if candidate.is_file():
            font_manager.fontManager.addfont(str(candidate))
            name=font_manager.FontProperties(fname=str(candidate)).get_name()
            if "arial" not in name.casefold():
                raise ValueError(f"Expected Arial font, found {name!r}: {candidate}")
    try:
        path=font_manager.findfont(font_manager.FontProperties(family="Arial",weight="normal"),
                                   fallback_to_default=False)
    except ValueError as exc:
        raise RuntimeError("Arial is required. Install Arial, or set ARIAL_FONT_PATH to an Arial font file.") from exc
    plt.rcParams.update({"font.family":"Arial","font.size":FONT_SIZE,"font.weight":"normal",
                         "axes.labelweight":"normal","svg.fonttype":"none",
                         "figure.facecolor":"white","axes.facecolor":"white",
                         "savefig.facecolor":"white","savefig.transparent":False})
    return path


def overall_similarity(rows):
    per_trial=[]
    for column in range(len(TRIAL_NUMBERS)):
        values=[row["matches"][column] for row in rows if row["matches"][column] is not None]
        per_trial.append(100*sum(values)/len(values) if values else None)
    valid=sum(row["valid_count"] for row in rows)
    same=sum(row["same_count"] for row in rows)
    return per_trial,100*same/valid if valid else None


def percentage_text(value):
    if value is None:
        return "N/A"
    return f"{value:.2f}".rstrip("0").rstrip(".")+"%"


def clean_png_svg(rows,stem,output,term_header):
    # 按两张标注图：Arial、全居中、纯白底、常规字重，只留表头下方一条横线。
    configure_arial()
    count=len(rows)+int(ADD_OVERALL_ROW)
    trial_x=[1.7+index for index in range(len(TRIAL_NUMBERS))]
    label_x,percentage_x=0.6,12.4
    fig,ax=plt.subplots(figsize=(FIGURE_WIDTH_IN,ROW_HEIGHT_IN*(count+1)+.15))
    ax.set_xlim(0,13.6);ax.set_ylim(.45,count+1.25);ax.axis("off")
    text_style=dict(fontsize=FONT_SIZE,fontfamily="Arial",fontweight="normal",ha="center",va="center")
    ax.text(label_x,count+.75,term_header,**text_style)
    for x,trial in zip(trial_x,TRIAL_NUMBERS):
        ax.text(x,count+.75,f"Trial {trial}",**text_style)
    ax.text(percentage_x,count+.75,"Sign similarity (%)",**text_style)
    ax.plot([0,13.6],[count+.35,count+.35],color="black",lw=.8)
    for index,row in enumerate(rows):
        y=count-index
        ax.text(label_x,y,row["term"],**text_style)
        for x,status in zip(trial_x,row["matches"]):
            color=UNKNOWN_COLOR if status is None else SAME_COLOR if status else DIFFERENT_COLOR
            ax.scatter(x,y,s=DOT_SIZE,marker="o",facecolors=color,
                       edgecolors=DOT_EDGE_COLOR,linewidths=DOT_EDGE_WIDTH)
        ax.text(percentage_x,y,percentage_text(row["same_percent"]),**text_style)
    if ADD_OVERALL_ROW:
        per_trial,overall=overall_similarity(rows)
        ax.text(label_x,1,"Overall",**text_style)
        for x,value in zip(trial_x,per_trial):
            ax.text(x,1,percentage_text(value),**text_style)
        ax.text(percentage_x,1,percentage_text(overall),**text_style)
    fig.subplots_adjust(left=.01,right=.99,top=.99,bottom=.01)
    for extension in ("png","svg"):
        fig.savefig(output/f"{stem}.{extension}",dpi=SAVE_DPI,bbox_inches="tight",pad_inches=.04)
    plt.close(fig)


def clean_csv_html(rows,stem,output,term_header):
    columns=[term_header]+[f"Trial {t}" for t in TRIAL_NUMBERS]+["Sign similarity (%)"]
    values=[]
    for row in rows:
        statuses=["Unavailable" if status is None else "Same" if status else "Different" for status in row["matches"]]
        values.append([row["term"]]+statuses+[row["same_percent"]])
    if ADD_OVERALL_ROW:
        per_trial,overall=overall_similarity(rows)
        values.append(["Overall"]+per_trial+[overall])
    pd.DataFrame(values,columns=columns).to_csv(output/f"{stem}.csv",index=False,encoding="utf-8-sig")
    parts=['<!doctype html><html><head><meta charset="utf-8"><style>',
           'body{margin:12px;background:white;font-family:Arial,sans-serif}',
           f'table{{border-collapse:collapse;min-width:1080px;font-size:{FONT_SIZE}pt;background:white}}',
           'th,td{padding:8px 16px;text-align:center;vertical-align:middle;white-space:nowrap;font-weight:normal;border:0;background:white}',
           'thead{border-bottom:1px solid black}',
           f'.dot{{display:inline-block;width:13px;height:13px;border-radius:50%;border:{DOT_EDGE_WIDTH}pt solid {DOT_EDGE_COLOR};box-sizing:border-box}}',
           '</style></head><body><table><thead><tr>']
    parts.extend(f'<th>{html.escape(c)}</th>' for c in columns)
    parts.append('</tr></thead><tbody>')
    for row in rows:
        parts.append(f'<tr><td>{html.escape(row["term"])}</td>')
        for status in row["matches"]:
            color=UNKNOWN_COLOR if status is None else SAME_COLOR if status else DIFFERENT_COLOR
            meaning="Unavailable" if status is None else "Same" if status else "Different"
            parts.append(f'<td><span class="dot" style="background:{color}" title="{meaning}"></span></td>')
        pct=percentage_text(row["same_percent"])
        parts.append(f'<td>{pct}</td></tr>')
    if ADD_OVERALL_ROW:
        per_trial,overall=overall_similarity(rows)
        parts.append('<tr><td>Overall</td>')
        parts.extend(f'<td>{percentage_text(value)}</td>' for value in per_trial+[overall])
        parts.append('</tr>')
    parts.append('</tbody></table></body></html>')
    (output/f"{stem}.html").write_text(''.join(parts),encoding="utf-8")


def save_comparison(rows,stem,output,term_header,basis):
    clean_png_svg(rows,stem,output,term_header)
    clean_csv_html(rows,stem,output,term_header)
    # Ref.和计数放入单独核对文件，不加入用户要求的简洁表格。
    pd.DataFrame([{"Term":r["term"],"Reference_sign":r["reference_sign"],
                   **{f"Trial-{t}_sign":s for t,s in zip(TRIAL_NUMBERS,r["trial_signs"])},
                   "Same_count":r["same_count"],"Valid_count":r["valid_count"],
                   "Same_percent":r["same_percent"],"Comparison_basis":basis}
                  for r in rows]).to_csv(output/f"{stem}_audit.csv",index=False,encoding="utf-8-sig")


def locate_ep_sources(root):
    candidates=[Path(EP_RAW_ROOT)] if EP_RAW_ROOT is not None else [root,root.parent]
    reasons=[]
    for candidate in candidates:
        try:return discover_sources(candidate)
        except (FileNotFoundError,ValueError) as exc:reasons.append(f"{candidate}: {exc}")
    raise FileNotFoundError("Ep needs raw data; old signed-log ordinates do not identify physical signs.\n"+'\n'.join(reasons))


def ep_comparisons(root,output):
    reference_path=find_picture(root,"Ep")
    fold_path=find_picture(root,"Ep-10 fold")
    sources=locate_ep_sources(root)
    endpoints=[]
    for trial in TRIAL_NUMBERS:
        values,_=extract_trial(trial,sources[trial])
        endpoints.extend(values)
    endpoints=pd.DataFrame(endpoints)
    if len(endpoints)!=140:raise ValueError("Expected140rawEp endpoints")
    endpoints.to_csv(output/"Ep_raw_values.csv",index=False,encoding="utf-8-sig")
    totals=[]
    for pct,_ in CONDITIONS:
        subset=endpoints[endpoints.CO2_percent==pct]
        trials={t:{int(r.Feature_id):int(r.Eprime_sign)
                   for _,r in subset[subset.Trial==t].iterrows()} for t in TRIAL_NUMBERS}
        rows=make_rows(EP_REFERENCE_SIGNS[pct],trials,[i for i,_ in FEATURES])
        save_comparison(rows,f"Ep_{pct}pct_sign_comparison",output,"E′","Raw physical Eprime")
        totals.append((f"Ep_{pct}pct",rows))
    response=[]
    for (trial,feature),group in endpoints.groupby(["Trial","Feature_id"]):
        low=group[group.CO2_percent==5].Eprime_mean.iloc[0]
        high=group[group.CO2_percent==100].Eprime_mean.iloc[0]
        response.append({"Trial":trial,"Feature_id":feature,"Eprime_5pct":low,
                         "Eprime_100pct":high,"Difference_100_minus_5":high-low})
    pd.DataFrame(response).to_csv(output/"Ep_raw_response_100_minus_5.csv",index=False,encoding="utf-8-sig")
    return totals,reference_path,fold_path


def main(root=ROOT_DIR):
    root=Path(root).resolve()
    output=root/OUTPUT_FOLDER
    if USE_RUN_SUBFOLDERS:output=output/datetime.now().strftime("run_%Y%m%d_%H%M%S_%f")
    output.mkdir(parents=True,exist_ok=True)
    statuses=[];summaries=[]
    for key,reference_stem,trial_stem in EPP_CASES:
        try:
            reference_path=find_picture(root,reference_stem)
            trial_path=find_picture(root,trial_stem)
            reference,trials,audit=image_pair_signs(reference_path,trial_path)
            rows=make_rows(reference,trials,PAIRS)
            save_comparison(rows,f"{key}_sign_comparison",output,"E″","Epp cell fill colors (red positive, blue negative)")
            (output/f"{key}_image_audit.json").write_text(json.dumps(audit,indent=2),encoding="utf-8")
            same=sum(r["same_count"] for r in rows);valid=sum(r["valid_count"] for r in rows)
            summaries.append({"Comparison":key,"Same_count":same,"Valid_count":valid,
                              "Same_percent":100*same/valid if valid else None})
            statuses.append({"Comparison":key,"Status":"Completed","Reason":"",
                             "Reference_file":str(reference_path),"Trial_file":str(trial_path)})
            print(f"[Completed] {key}: {same}/{valid}")
        except Exception as exc:
            statuses.append({"Comparison":key,"Status":"Failed","Reason":str(exc)})
            print(f"[Not completed] {key}: {exc}")
    try:
        groups,reference_path,fold_path=ep_comparisons(root,output)
        for key,rows in groups:
            same=sum(r["same_count"] for r in rows);valid=sum(r["valid_count"] for r in rows)
            summaries.append({"Comparison":key,"Same_count":same,"Valid_count":valid,
                              "Same_percent":100*same/valid if valid else None})
            print(f"[Completed] {key}: {same}/{valid}")
        statuses.append({"Comparison":"Ep","Status":"Completed","Reason":"Raw-data physical sign comparison",
                         "Reference_file":str(reference_path),"Trial_file":str(fold_path)})
    except Exception as exc:
        statuses.append({"Comparison":"Ep","Status":"Requires raw data","Reason":str(exc)})
        print(f"[Ep requires raw data] {exc}")
    pd.DataFrame(statuses).to_csv(output/"comparison_status.csv",index=False,encoding="utf-8-sig")
    pd.DataFrame(summaries).to_csv(output/"comparison_summary.csv",index=False,encoding="utf-8-sig")
    overall_summary=[]
    for summary in summaries:
        overall_summary.append({"Comparison":summary["Comparison"],
                                "Same count":summary["Same_count"],
                                "Valid count":summary["Valid_count"],
                                "Overall sign similarity (%)":summary["Same_percent"]})
    pd.DataFrame(overall_summary).to_csv(output/"overall_sign_similarity.csv",index=False,encoding="utf-8-sig")
    print(f"Saved: {output}")
    print("Pink solid dot = same sign; blue solid dot = different sign. No display window is used.")
    return statuses,summaries


def image_cells(path, expected_count):
    """定位有颜色填充的方格；依赖严格的数量和几何检查，识别不全时报错。"""
    from PIL import Image
    from scipy import ndimage
    pixels = np.asarray(Image.open(path).convert("RGB"), dtype=np.int16)
    chromatic = ((pixels.max(2) - pixels.min(2) > 1)
                 & (pixels.min(2) > 80) & (pixels.max(2) > 150))
    labels, _ = ndimage.label(chromatic)
    candidates = []
    rectangles = []
    for number, slices in enumerate(ndimage.find_objects(labels), 1):
        if slices is None:
            continue
        ys, xs = slices
        h, w = ys.stop - ys.start, xs.stop - xs.start
        if min(h, w) < 20:
            continue
        if np.count_nonzero(labels[slices] == number) / (h * w) < 0.45:
            continue
        if 0.7 < w / h < 1.3:
            candidates.append((xs.start, ys.start, w, h))
        elif w > h:
            rectangles.append((xs.start, ys.start, w, h))
    if not candidates:
        raise ValueError(f"No colored matrix cells found in {path}")
    # 保留接近零的浅色负值方格；排除参考图较小的彩色编号和标记。
    size = max(min(w, h) for _, _, w, h in candidates)
    cells = [c for c in candidates if min(c[2:]) >= 0.9 * size]
    # 总图缩小后，中间列部分网格边界变浅，同色相邻方格可能连通。
    # 将高度为一个方格、宽度为2~7个方格的横向连通区域等分，避免漏项。
    for x, y, w, h in rectangles:
        if not 0.9 * size <= h <= 1.1 * size:
            continue
        count = round((w + 1) / (size + 1))
        if not 2 <= count <= 7 or abs((w + 1) / count - (size + 1)) > 2:
            continue
        edges = np.rint(np.linspace(x, x + w, count + 1)).astype(int)
        cells.extend((int(edges[k]), y, int(edges[k+1] - edges[k]), h) for k in range(count))
    if len(cells) != expected_count:
        raise ValueError(f"Expected {expected_count} colored cells, found {len(cells)} in {path}; use numeric CSVs")
    enriched = []
    for x, y, w, h in cells:
        margin = max(2, round(min(w, h) * 0.15))
        crop = pixels[y + margin:y + h - margin, x + margin:x + w - margin]
        difference = float(np.median(crop[:, :, 0] - crop[:, :, 2]))
        if abs(difference) < 1:
            raise ValueError(f"Ambiguous near-neutral cell at {(x, y)} in {path}; use numeric CSVs")
        enriched.append({"x": x, "y": y, "w": w, "h": h,
                         "sign": 1 if difference > 0 else -1, "median_R_minus_B": difference})
    return enriched, pixels.shape[:2]

def cells_to_pairs(cells):
    if len(cells) != 28:
        raise ValueError("Each panel must contain 28 colored cells")
    tolerance = 0.4 * np.median([c["h"] for c in cells])
    groups = []
    for cell in sorted(cells, key=lambda c: c["y"] + c["h"] / 2):
        center = cell["y"] + cell["h"] / 2
        if not groups or abs(center - np.mean([c["y"] + c["h"]/2 for c in groups[-1]])) > tolerance:
            groups.append([])
        groups[-1].append(cell)
    if [len(row) for row in groups] != list(range(1, 8)):
        raise ValueError("The detected panel is not a complete 7x7 lower triangle")
    result = {}
    for i, group in enumerate(groups):
        for j, cell in enumerate(sorted(group, key=lambda c: c["x"])):
            result[(FEATURES[i][0], FEATURES[j][0])] = cell["sign"]
    return result

def physical_sign(value):
    if not np.isfinite(value):
        return 0
    return 0 if abs(value) <= ZERO_TOLERANCE else (1 if value > 0 else -1)

def kobs(co2_fraction):
    fraction = np.asarray(co2_fraction, dtype=float)
    return KOBS_K0 + KOBS_KMAX * KOBS_K * fraction / (1 + KOBS_K * fraction)

def discover_sources(root):
    found = {}
    for folder in root.iterdir():
        match = re.fullmatch(r"trial[ _-]*(\d+)", folder.name, re.I)
        if folder.is_dir() and match and int(match[1]) in TRIAL_NUMBERS:
            number = int(match[1])
            if number in found:
                raise ValueError(f"Duplicate folders for Trial-{number}")
            found[number] = folder
    missing = sorted(set(TRIAL_NUMBERS) - set(found))
    if missing:
        raise FileNotFoundError(
            f"Missing Trial folders: {missing}. Place this script beside Trial-1 ... Trial-10."
        )
    sources = {}
    for number, folder in found.items():
        candidates = [p for p in folder.rglob(SOURCE_FILE)
                      if re.match(r"^step[ _-]*5(?:\D|$)", p.parent.name, re.I)]
        if len(candidates) != 1:
            raise FileNotFoundError(
                f"Trial-{number}: expected one Step5/{SOURCE_FILE}; found {candidates}"
            )
        sources[number] = candidates[0]
    return sources

def load_coefficients(path):
    with path.open(encoding="utf-8-sig", newline="") as file:
        header = next(csv.reader(file))
    if len(header) != len(set(header)):
        raise ValueError(f"Duplicate CSV column names in {path}")
    df = pd.read_csv(path, index_col=0, encoding="utf-8-sig")
    df.index = df.index.map(lambda value: str(value).strip())
    if not df.index.is_unique:
        raise ValueError(f"Duplicate feature names in {path}")
    parsed = []
    for column in df.columns:
        if column.startswith("mean_Ci_"):
            try:
                fraction = float(column[len("mean_Ci_"):])
            except ValueError as exc:
                raise ValueError(f"Invalid CO2 column: {column} in {path}") from exc
            parsed.append((fraction, column))
    parsed.sort()
    fractions = np.array([fraction for fraction, _ in parsed], dtype=float)
    if not len(fractions) or not np.isfinite(fractions).all():
        raise ValueError(f"No usable mean_Ci_* columns in {path}")
    if len(np.unique(fractions)) != len(fractions) or np.any((fractions < 0) | (fractions > 1)):
        raise ValueError(f"CO2 suffixes must be unique fractions between0and1 in {path}")
    columns = [column for _, column in parsed]
    for _, name, _ in EP_FEATURES:
        if name not in df.index or f"{name}*CO2" not in df.index:
            raise ValueError(f"Missing {name!r} or its *CO2 coefficient in {path}")
    return df, fractions, columns

def feature_values(df, name, fractions, columns):
    concentrations = CO2_MAX_M * fractions
    intercept = pd.to_numeric(df.loc[name, columns], errors="raise").to_numpy(dtype=float)
    slope = pd.to_numeric(df.loc[f"{name}*CO2", columns], errors="raise").to_numpy(dtype=float)
    if not np.isfinite(intercept).all() or not np.isfinite(slope).all():
        raise ValueError(f"Non-finite coefficients for {name}")
    ai = intercept + slope * concentrations
    rate = kobs(fractions)
    if R <= 0 or T <= 0 or not np.isfinite(rate).all() or np.any(rate <= 0):
        raise ValueError("R,T and every kobs value must be finite and positive")
    factor = -(R * T / 2.0) / rate
    eprime = factor * ai
    std_columns = [column.replace("mean_", "std_", 1) for column in columns]
    if all(column in df.columns for column in std_columns):
        b_std = pd.to_numeric(df.loc[name, std_columns], errors="raise").to_numpy(dtype=float)
        k_std = pd.to_numeric(df.loc[f"{name}*CO2", std_columns], errors="raise").to_numpy(dtype=float)
        if np.isinf(b_std).any() or np.isinf(k_std).any() or np.any(b_std < 0) or np.any(k_std < 0):
            raise ValueError(f"Invalid coefficient STD for {name}")
        # 沿用原绘图代码：不考虑斜率/截距协方差、kobs拟合不确定度。
        ai_std = np.hypot(b_std, concentrations * k_std)
        eprime_std = np.abs(factor) * ai_std
    else:
        ai_std = np.full_like(ai, np.nan)
        eprime_std = np.full_like(ai, np.nan)
    if not np.isfinite(eprime).all():
        raise ValueError(f"Eprime overflow for {name}")
    return ai, ai_std, rate, eprime, eprime_std

def extract_trial(trial, path):
    df, fractions, columns = load_coefficients(path)
    endpoints, curves = [], []
    target_indices = {}
    for pct, fraction in CONDITIONS:
        matches = np.flatnonzero(np.isclose(fractions, fraction, rtol=0, atol=1e-10))
        if len(matches) != 1:
            raise ValueError(
                f"Trial-{trial}: exact {pct}% CO2 column missing in {path}; interpolation was not performed."
            )
        target_indices[pct] = int(matches[0])
    for feature_id, name, color in EP_FEATURES:
        ai, ai_std, rate, eprime, eprime_std = feature_values(df, name, fractions, columns)
        curves.append({"trial": trial, "feature_id": feature_id, "name": name, "color": color,
                       "x": CO2_MAX_M * fractions, "mean": eprime, "std": eprime_std})
        for pct, fraction in CONDITIONS:
            index = target_indices[pct]
            sign = physical_sign(eprime[index])
            reference = EP_REFERENCE_SIGNS[pct][feature_id]
            endpoints.append({
                "Trial": trial, "Feature_id": feature_id, "Feature": name,
                "CO2_percent": pct, "CO2_fraction": fraction, "CO2_M": CO2_MAX_M * fraction,
                "Ai_mean": ai[index], "Ai_std": ai_std[index], "kobs": rate[index],
                "Eprime_mean": eprime[index], "Eprime_std": eprime_std[index],
                "Eprime_sign": sign, "Reference_sign": reference,
                "Same_sign": int(sign == reference) if sign != 0 and reference != 0 else np.nan,
                "Source_file": str(path),
            })
    return endpoints, curves


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,default=ROOT_DIR)
    args=parser.parse_args()
    main(args.root)
