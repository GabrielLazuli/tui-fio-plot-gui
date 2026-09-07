#!/usr/bin/env python3
"""
FIO Plot Automation - Graphical Application
Generates charts from FIO benchmark results selected as DIRECTORIES.

Criado por: Gabriel Souza e Bruno Costa
Projeto associado à disciplina de Organização e Recuperação da Informação
Professor: Sérgio Fred Ribeiro Andrade
"""

import csv
import json
import os
import shutil
import sys
import tempfile
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from fio_plot.fiolib import (
    defaultsettings,
    getdata,
    bar2d,
    barhistogram,
    graph2d,
    dataimport,
)

RWMODES = ["read", "write", "randread", "randwrite", "randrw", "trim"]
RESULT_JSON_NAME = "resultado.json"


def _return_folder_name_basename(filename, settings, override=False):
    """Show only the innermost folder name on the chart labels and merge keys."""
    path = os.path.normpath(filename)
    if override or not os.path.isdir(path):
        path = os.path.dirname(path)
    base = os.path.basename(path)
    if not base:
        base = path
    return base


dataimport.return_folder_name = _return_folder_name_basename
VALID_TYPES = ["bw", "iops", "lat", "slat", "clat"]

TMP_ROOT = tempfile.mkdtemp(prefix="fio_plot_automacao_")


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def pause():
    try:
        input("\n  Pressione Enter para continuar...")
    except (ValueError, EOFError):
        print()


def ask(prompt, options, allow_blank=False):
    """Menu textual genérico."""
    print(prompt)
    while True:
        raw = input("\n  > ").strip()
        if allow_blank and raw == "":
            return None
        if raw in options:
            return raw
        print(f"  Opção inválida. Escolha: {', '.join(options)}")


# ========================
# Directory helpers
# ========================

def find_result_json(directory):
    if os.path.isdir(directory):
        candidate = os.path.join(directory, RESULT_JSON_NAME)
        if os.path.isfile(candidate):
            return candidate
        jsons = [os.path.join(directory, f) for f in os.listdir(directory)
                 if f.lower().endswith(".json")]
        if len(jsons) == 1:
            return jsons[0]
    return None


def find_log_files(directory):
    if not os.path.isdir(directory):
        return []
    logs = [os.path.join(directory, f) for f in os.listdir(directory)
            if f.endswith(".log")]
    return sorted(logs)


def detect_workload(json_path):
    with open(json_path, encoding="utf-8") as fh:
        data = json.load(fh)
    job_options = data["jobs"][0].get("job options", {})
    opts = dict(job_options)
    global_options = data.get("global options", {})
    if isinstance(global_options, dict):
        for k, v in global_options.items():
            opts.setdefault(k, v)
    elif isinstance(global_options, list) and global_options and isinstance(global_options[0], dict):
        for k, v in global_options[0].items():
            opts.setdefault(k, v)
    return {
        "rw": opts.get("rw"),
        "iodepth": opts.get("iodepth"),
        "numjobs": opts.get("numjobs"),
    }


def detect_log_type(log_path):
    base = os.path.basename(log_path)
    stem = base.split(".")[0]
    parts = stem.rsplit("_", 1)
    if len(parts) == 2 and parts[1] in VALID_TYPES:
        return parts[1]
    return None


def detect_log_job_number(log_path):
    base = os.path.basename(log_path)
    parts = base.split(".")
    for part in parts[:-1]:
        if part.isdigit():
            return part
    return None


def stage_dir_json(bench_dir):
    json_file = find_result_json(bench_dir)
    if not json_file:
        return None
    name = os.path.basename(os.path.normpath(bench_dir)) or "benchmark"
    d = os.path.join(TMP_ROOT, name)
    os.makedirs(d, exist_ok=True)
    shutil.copy2(json_file, os.path.join(d, os.path.basename(json_file)))
    return d


def aggregate_log_file(src, dst, logtype, bin_ms=1000):
    bins = {"0": {}, "1": {}}
    with open(src, encoding="utf-8") as fh:
        reader = csv.reader(fh)
        for row in reader:
            try:
                ts_ms = int(row[0])
                value = float(row[1])
                rwt = row[2].strip()
            except (ValueError, IndexError):
                continue
            if rwt not in bins:
                continue
            b = int(ts_ms / bin_ms)
            acc = bins[rwt].setdefault(b, [0, 0.0])
            acc[0] += 1
            acc[1] += value

    if all(not v for v in bins.values()):
        return False

    last_bin = 0
    for rwt in bins:
        if bins[rwt]:
            last_bin = max(last_bin, max(bins[rwt]))

    with open(dst, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        for rwt in ("0", "1"):
            for b in range(last_bin + 1):
                acc = bins[rwt].get(b)
                if acc is None:
                    value = 0
                elif logtype == "iops":
                    value = int(acc[1])
                elif logtype == "bw":
                    value = int(acc[1])
                else:
                    value = int(acc[1] / acc[0]) if acc[0] else 0
                writer.writerow([b * bin_ms, value, rwt, 4096, 0])
    return True


def stage_dir_logs(bench_dir, rw, iodepth, numjobs, logtype):
    json_file = find_result_json(bench_dir)
    name = os.path.basename(os.path.normpath(bench_dir)) or "benchmark"
    d = os.path.join(TMP_ROOT, name)
    os.makedirs(d, exist_ok=True)
    if json_file:
        shutil.copy2(json_file, os.path.join(d, os.path.basename(json_file)))
    for log in find_log_files(bench_dir):
        job = detect_log_job_number(log)
        newname = f"{rw}-iodepth-{iodepth}-numjobs-{numjobs}_{logtype}"
        if job:
            newname += f".{job}.log"
        else:
            newname += ".log"
        aggregate_log_file(log, os.path.join(d, newname), logtype)
    return d


def browse_directory(title="Selecione uma pasta"):
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    path = filedialog.askdirectory(title=title)
    root.destroy()
    return path if path else None


def gather_directories(multi=False, title="Selecione as pastas de benchmark"):
    def _show_selected():
        if selected:
            print(f"\n  Selecionadas ({len(selected)}):")
            for s in selected:
                print(f"    - {os.path.basename(s)}")

    selected = []
    if multi:
        print(f"\n  {title}")
        print("  Escolha uma pasta no diálogo; você pode adicionar mais depois.\n")
        while True:
            path = browse_directory(title)
            if not path:
                if selected:
                    break
                print("  Nenhuma pasta selecionada.")
                continue
            path = os.path.abspath(path)
            if path in selected:
                print(f"  [!] Já adicionada: {os.path.basename(path)}")
            else:
                selected.append(path)
                print(f"  Adicionada: {os.path.basename(path)}")
            _show_selected()
            more = input("\n  Adicionar outra pasta? [s/N] > ").strip().lower()
            if not more or more in ("n", "nao", "não", "0"):
                break
            if more not in ("s", "sim", "y", "yes"):
                print("  (considerado como 'não')")
                break
    else:
        path = browse_directory(title)
        if path and os.path.isdir(path):
            selected.append(os.path.abspath(path))
            print(f"  Selecionada: {os.path.basename(path)}")
        else:
            print("  Nenhuma pasta selecionada.")

    if len(selected) > 1:
        _show_selected()
    return selected


# ========================
# Workload / filter config
# ========================

def gather_rw_filter(settings):
    print("\n  Modo de dados (--rw):")
    for i, mode in enumerate(RWMODES, 1):
        print(f"  [{i}] {mode}")
    choice = ask("  Escolha o modo que corresponde ao seu benchmark:",
                 [str(i) for i in range(1, len(RWMODES) + 1)])
    settings["rw"] = RWMODES[int(choice) - 1]

    if settings["rw"] in ("randrw", "readwrite"):
        print("\n  Filtro (leitura/escrita) para dados randrw:")
        print("  [1] read (padrão)")
        print("  [2] write")
        f = ask("  Escolha o filtro:", ["1", "2"], allow_blank=True)
        settings["filter"] = ["read"] if f != "2" else ["write"]
    elif settings["rw"] == "rw":
        print("\n  Filtro (leitura/escrita) para dados rw:")
        print("  [1] read")
        print("  [2] write")
        print("  [3] both (padrão)")
        f = ask("  Escolha o filtro:", ["1", "2", "3"], allow_blank=True)
        if f == "1":
            settings["filter"] = ["read"]
        elif f == "2":
            settings["filter"] = ["write"]
        else:
            settings["filter"] = ["read", "write"]


def gather_title_source(settings):
    title = input("\n  Título do gráfico (Enter para o padrão): ").strip()
    settings["title"] = title or "Resultados de Benchmark FIO"
    source = input("  Fonte/autor (Enter para pular): ").strip()
    settings["source"] = source or None


def build_base_settings():
    settings = defaultsettings.get_default_settings()
    settings.setdefault("input_directory", [])
    settings.setdefault("title", None)
    settings.setdefault("source", None)
    settings.setdefault("rw", None)
    settings.setdefault("iodepth", None)
    settings.setdefault("numjobs", None)
    settings.setdefault("graphtype", None)
    settings.setdefault("output_filename", None)
    for gt in ["bargraph3d", "bargraph2d_qd", "bargraph2d_nj",
               "histogram", "loggraph", "compare_graph"]:
        settings.setdefault(gt, False)
    return settings


# ========================
# 1) 2D Chart
# ========================

def chart_compare(settings):
    print("\n  COMPARAR RESULTADOS DE BENCHMARK (Gráfico de Barras 2D)")
    print("  Selecione VÁRIAS pastas de benchmark para comparar (um run por pasta).\n")

    dirs = gather_directories(multi=True, title="Selecione as pastas de benchmark para comparar")
    if not dirs:
        print("\n  Nenhuma pasta selecionada.")
        return
    if len(dirs) < 2:
        print("\n  [!] É necessário selecionar pelo menos duas pastas para comparar.")
        return

    staged = {}
    for d in dirs:
        if not find_result_json(d):
            print(f"\n  [!] Nenhum JSON do FIO encontrado em: {d}")
            return
        staged[d] = stage_dir_json(d)
        print(f"  - {os.path.basename(os.path.normpath(d))}")

    settings["input_directory"] = list(staged.values())
    workloads = [detect_workload(find_result_json(d)) for d in dirs]
    rws = {w["rw"] for w in workloads}
    iodepths = {int(w["iodepth"]) for w in workloads if w["iodepth"]}
    numjobs = {int(w["numjobs"]) for w in workloads if w["numjobs"]}

    if len(rws) == 1 and len(iodepths) == 1 and len(numjobs) == 1:
        settings["rw"] = rws.pop()
        settings["iodepth"] = [iodepths.pop()]
        settings["numjobs"] = [numjobs.pop()]
        print(f"\n  Workload detectado automaticamente: rw={settings['rw']}, "
              f"iodepth={settings['iodepth'][0]}, numjobs={settings['numjobs'][0]}")
        if settings["rw"] in ("randrw", "readwrite"):
            print("  [1] read (padrão)\n  [2] write")
            f = ask("  Filtro (leitura/escrita) para dados randrw:", ["1", "2"], allow_blank=True)
            settings["filter"] = ["read"] if f != "2" else ["write"]
        else:
            print("  [1] read\n  [2] write\n  [3] both (padrão)")
            f = ask("  Filtro (leitura/escrita) para dados rw:", ["1", "2", "3"], allow_blank=True)
            if f == "1":
                settings["filter"] = ["read"]
            elif f == "2":
                settings["filter"] = ["write"]
            else:
                settings["filter"] = ["read", "write"]
    else:
        print("\n  [!] Os arquivos têm valores diferentes de rw/iodepth/numjobs.")
        gather_rw_filter(settings)
        gather_iodepth_numjobs(settings, require_both=True)

    gather_title_source(settings)
    settings["graphtype"] = "compare_graph"
    settings["compare_graph"] = True

    routing = getdata.get_routing_dict()
    settings = getdata.configure_default_settings(settings, routing, "compare_graph")
    data = getdata.get_json_data(settings)
    bar2d.compchart_2dbarchart_jsonlogdata(settings, data)


def gather_iodepth_numjobs(settings, require_both=True):
    print("\n  O fio-plot precisa de iodepth e numjobs que correspondam aos seus dados.")
    if require_both:
        iodepth = ask("  iodepth: ", [str(x) for x in range(1, 129)])
        numjobs = ask("  numjobs: ", [str(x) for x in range(1, 129)])
        settings["iodepth"] = [int(iodepth)]
        settings["numjobs"] = [int(numjobs)]
    else:
        iodepth = ask("  iodepth (Enter para o padrão): ", [str(x) for x in range(1, 129)], allow_blank=True)
        numjobs = ask("  numjobs (Enter para o padrão): ", [str(x) for x in range(1, 129)], allow_blank=True)
        settings["iodepth"] = [int(iodepth)] if iodepth else None
        settings["numjobs"] = [int(numjobs)] if numjobs else None
    return settings


# ========================
# 2) Gráfico de Linha 
# ========================

def chart_log(settings):
    print("\n  GRÁFICO DE LINHA A PARTIR DOS LOGS DO FIO")
    print("  Selecione uma pasta de benchmark contendo seus arquivos *.N.log.\n")

    dirs = gather_directories(multi=False, title="Selecione a pasta de benchmark")
    if not dirs:
        print("\n  Nenhuma pasta selecionada.")
        return
    bench_dir = dirs[0]

    json_file = find_result_json(bench_dir)
    logs = find_log_files(bench_dir)
    if not logs:
        print(f"\n  [!] Nenhum arquivo .log encontrado em: {bench_dir}")
        return
    if not json_file:
        print(f"\n  [!] Nenhum JSON do FIO encontrado em: {bench_dir} (necessário para detectar o workload).")
        return

    workload = detect_workload(json_file)
    if not all(workload.values()):
        print("\n  [!] Não foi possível detectar rw/iodepth/numjobs a partir do JSON.")
        gather_rw_filter(settings)
        gather_iodepth_numjobs(settings, require_both=True)
    else:
        settings["rw"] = workload["rw"]
        settings["iodepth"] = [int(workload["iodepth"])]
        settings["numjobs"] = [int(workload["numjobs"])]
        print(f"\n  Workload detectado automaticamente: rw={settings['rw']}, "
              f"iodepth={settings['iodepth'][0]}, numjobs={settings['numjobs'][0]}")

    logtype = detect_log_type(logs[0])
    if not logtype:
        print("\n  Não foi possível detectar o tipo de métrica a partir do nome do log.")
        print("  Tipos: " + ", ".join(VALID_TYPES))
        choice = ask("  Escolha a métrica:",
                     [str(i) for i in range(1, len(VALID_TYPES) + 1)])
        logtype = VALID_TYPES[int(choice) - 1]
    settings["type"] = [logtype]
    print(f"  Tipo de métrica detectado: {logtype}")

    iodepth = settings["iodepth"][0]
    numjobs = settings["numjobs"][0]
    settings["input_directory"] = [stage_dir_logs(bench_dir, settings["rw"], iodepth, numjobs, logtype)]

    if settings["rw"] in ("randrw", "readwrite"):
        settings["filter"] = ["read", "write"]
    else:
        settings["filter"] = ["read", "write"]

    gather_title_source(settings)
    settings["graphtype"] = "loggraph"
    settings["loggraph"] = True

    routing = getdata.get_routing_dict()
    settings = getdata.configure_default_settings(settings, routing, "loggraph")
    data = getdata.get_log_data(settings)
    graph2d.chart_2d_log_data(settings, data)


# ========================
# 3) Histograma
# ========================

def chart_histogram(settings):
    print("\n  HISTOGRAMA DE LATÊNCIA")
    print("  Selecione uma pasta de benchmark contendo o resultado JSON do FIO.\n")

    dirs = gather_directories(multi=False, title="Selecione a pasta de benchmark")
    if not dirs:
        print("\n  Nenhuma pasta selecionada.")
        return
    bench_dir = dirs[0]

    json_file = find_result_json(bench_dir)
    if not json_file:
        print(f"\n  [!] Nenhum JSON do FIO encontrado em: {bench_dir}")
        return

    print(f"  - {os.path.basename(os.path.normpath(bench_dir))}")
    settings["input_directory"] = [stage_dir_json(bench_dir)]

    workload = detect_workload(json_file)
    if all(workload.values()):
        settings["rw"] = workload["rw"]
        settings["iodepth"] = [int(workload["iodepth"])]
        settings["numjobs"] = [int(workload["numjobs"])]
        print(f"\n  Workload detectado automaticamente: rw={settings['rw']}, "
              f"iodepth={settings['iodepth'][0]}, numjobs={settings['numjobs'][0]}")
        if settings["rw"] in ("randrw", "readwrite"):
            print("\n  Filtro (leitura/escrita):")
            print("  [1] read (padrão)")
            print("  [2] write")
            f = ask("  Escolha o filtro:", ["1", "2"], allow_blank=True)
            settings["filter"] = ["read"] if f != "2" else ["write"]
        else:
            print("\n  Filtro (leitura/escrita):")
            print("  [1] read")
            print("  [2] write")
            print("  [3] both (padrão)")
            f = ask("  Escolha o filtro:", ["1", "2", "3"], allow_blank=True)
            if f == "1":
                settings["filter"] = ["read"]
            elif f == "2":
                settings["filter"] = ["write"]
            else:
                settings["filter"] = ["read", "write"]
    else:
        gather_rw_filter(settings)
        gather_iodepth_numjobs(settings, require_both=True)

    gather_title_source(settings)
    settings["graphtype"] = "histogram"
    settings["histogram"] = True

    routing = getdata.get_routing_dict()
    settings = getdata.configure_default_settings(settings, routing, "histogram")
    data = getdata.get_json_data(settings)
    barhistogram.chart_latency_histogram(settings, data)


# ========================
# Output handling
# ========================

def make_output(settings):
    if not settings.get("output_filename"):
        title = (settings.get("title") or "fio_plot").replace(" ", "-").replace("/", "-")
        assets_dir = os.path.join(os.getcwd(), "assets")
        os.makedirs(assets_dir, exist_ok=True)
        settings["output_filename"] = os.path.join(assets_dir, f"{title}.png")
    settings["output_filename"] = os.path.abspath(settings["output_filename"])
    return settings


def open_image(settings):
    path = settings.get("output_filename")
    if path and os.path.exists(path):
        print(f"\n  Gráfico salvo em: {path}")
        try:
            if os.name == "nt":
                os.startfile(path)
            else:
                import subprocess
                subprocess.Popen(["xdg-open", path])
            print("  Abrindo gráfico...")
        except Exception as e:
            print(f"  Não foi possível abrir automaticamente: {e}")
    else:
        print("\n  [!] Não foi possível localizar o arquivo de saída.")


def run_plot(settings, func):
    try:
        settings = make_output(settings)
        func(settings)
        open_image(settings)
    except SystemExit:
        pass
    except Exception as e:
        print(f"\n  [ERRO] {type(e).__name__}: {e}")
    pause()


# ========================
# Graphical user interface
# ========================

def gui_select_directories(multi=False):
    selected = []
    while True:
        path = filedialog.askdirectory(
            title="Selecione uma pasta de benchmark",
            mustexist=True,
        )
        if not path:
            break
        path = os.path.abspath(path)
        if path not in selected:
            selected.append(path)
        if not multi:
            break
        if not messagebox.askyesno(
                "Adicionar outra pasta?",
                "Deseja adicionar outra pasta para comparação?",
        ):
            break
    return selected


def gui_ask_title_source():
    title = simpledialog.askstring(
        "Título do gráfico",
        "Informe o título (opcional):",
    ) or "Resultados de Benchmark FIO"
    source = simpledialog.askstring(
        "Fonte",
        "Informe a fonte ou autor (opcional):",
    )
    return title, source or None


def gui_choose_filter(rw, allow_both=False):
    if rw in ("randrw", "readwrite"):
        return ["write"] if messagebox.askyesno(
            "Filtro", "Mostrar escrita?\n\nEscolha Não para mostrar leitura."
        ) else ["read"]
    if allow_both:
        answer = messagebox.askyesnocancel(
            "Filtro",
            "Sim: somente escrita\nNão: somente leitura\nCancelar: leitura e escrita",
        )
        if answer is None:
            return ["read", "write"]
        return ["write"] if answer else ["read"]
    return ["read", "write"]


def gui_ask_workload(settings, allow_both=False):
    rw = simpledialog.askstring(
        "Modo de dados",
        "Informe o modo (--rw):\nread, write, randread, randwrite, randrw ou trim",
        initialvalue="randrw",
    )
    if rw not in RWMODES:
        raise ValueError("Modo de dados inválido.")
    iodepth = simpledialog.askinteger("I/O depth", "Informe o iodepth:", minvalue=1, maxvalue=128)
    numjobs = simpledialog.askinteger("Número de jobs", "Informe o numjobs:", minvalue=1, maxvalue=128)
    if iodepth is None or numjobs is None:
        raise ValueError("Os valores de iodepth e numjobs são obrigatórios.")
    settings["rw"] = rw
    settings["iodepth"] = [iodepth]
    settings["numjobs"] = [numjobs]
    settings["filter"] = gui_choose_filter(rw, allow_both=allow_both)


def gui_apply_workload(settings, json_file, allow_both=False):
    workload = detect_workload(json_file)
    if all(workload.values()):
        settings["rw"] = workload["rw"]
        settings["iodepth"] = [int(workload["iodepth"])]
        settings["numjobs"] = [int(workload["numjobs"])]
        settings["filter"] = gui_choose_filter(settings["rw"], allow_both=allow_both)
    else:
        gui_ask_workload(settings, allow_both=allow_both)


def gui_chart_compare():
    dirs = gui_select_directories(multi=True)
    if len(dirs) < 2:
        if dirs:
            messagebox.showwarning("Comparação", "Selecione pelo menos duas pastas.")
        return
    for directory in dirs:
        if not find_result_json(directory):
            raise ValueError(f"Nenhum JSON do FIO encontrado em:\n{directory}")

    settings = build_base_settings()
    settings["input_directory"] = [stage_dir_json(directory) for directory in dirs]
    workloads = [detect_workload(find_result_json(directory)) for directory in dirs]
    if (len({w["rw"] for w in workloads}) == 1
            and len({w["iodepth"] for w in workloads}) == 1
            and len({w["numjobs"] for w in workloads}) == 1
            and all(workloads[0].values())):
        settings["rw"] = workloads[0]["rw"]
        settings["iodepth"] = [int(workloads[0]["iodepth"])]
        settings["numjobs"] = [int(workloads[0]["numjobs"])]
        settings["filter"] = gui_choose_filter(settings["rw"], allow_both=True)
    else:
        gui_ask_workload(settings, allow_both=True)
    settings["title"], settings["source"] = gui_ask_title_source()
    settings = make_output(settings)
    settings["graphtype"] = "compare_graph"
    settings["compare_graph"] = True
    routing = getdata.get_routing_dict()
    settings = getdata.configure_default_settings(settings, routing, "compare_graph")
    bar2d.compchart_2dbarchart_jsonlogdata(settings, getdata.get_json_data(settings))
    return settings


def gui_chart_log():
    dirs = gui_select_directories()
    if not dirs:
        return
    bench_dir = dirs[0]
    json_file = find_result_json(bench_dir)
    logs = find_log_files(bench_dir)
    if not json_file:
        raise ValueError("A pasta selecionada não contém um JSON do FIO válido.")
    if not logs:
        raise ValueError("A pasta selecionada não contém arquivos .log.")
    settings = build_base_settings()
    gui_apply_workload(settings, json_file)
    logtype = detect_log_type(logs[0])
    if not logtype:
        logtype = simpledialog.askstring(
            "Métrica dos logs",
            "Informe a métrica (bw, iops, lat, slat ou clat):",
            initialvalue="iops",
        )
        if logtype not in VALID_TYPES:
            raise ValueError("Métrica de log inválida.")
    settings["type"] = [logtype]
    settings["input_directory"] = [stage_dir_logs(
        bench_dir, settings["rw"], settings["iodepth"][0], settings["numjobs"][0], logtype
    )]
    settings["filter"] = ["read", "write"]
    settings["title"], settings["source"] = gui_ask_title_source()
    settings = make_output(settings)
    settings["graphtype"] = "loggraph"
    settings["loggraph"] = True
    routing = getdata.get_routing_dict()
    settings = getdata.configure_default_settings(settings, routing, "loggraph")
    graph2d.chart_2d_log_data(settings, getdata.get_log_data(settings))
    return settings


def gui_chart_histogram():
    dirs = gui_select_directories()
    if not dirs:
        return
    bench_dir = dirs[0]
    json_file = find_result_json(bench_dir)
    if not json_file:
        raise ValueError("A pasta selecionada não contém um JSON do FIO válido.")
    settings = build_base_settings()
    settings["input_directory"] = [stage_dir_json(bench_dir)]
    gui_apply_workload(settings, json_file, allow_both=True)
    settings["title"], settings["source"] = gui_ask_title_source()
    settings = make_output(settings)
    settings["graphtype"] = "histogram"
    settings["histogram"] = True
    routing = getdata.get_routing_dict()
    settings = getdata.configure_default_settings(settings, routing, "histogram")
    barhistogram.chart_latency_histogram(settings, getdata.get_json_data(settings))
    return settings


def launch_gui_plot(plotter, status_label):
    try:
        status_label.config(text="Processando dados e gerando gráfico...")
        result = plotter()
        if result:
            open_image(result)
        status_label.config(text="Gráfico gerado com sucesso. Verifique a imagem aberta.")
    except Exception as error:
        status_label.config(text="Não foi possível gerar o gráfico.")
        messagebox.showerror("Erro ao gerar gráfico", f"{type(error).__name__}: {error}")


def main_gui():
    root = tk.Tk()
    root.title("FIO Plot Automation")
    root.geometry("750x620")
    root.minsize(700, 580)
    
    # Paleta de cores moderna (Catppuccin Macchiato inspirada)
    BG_MAIN = "#1E1E2E"
    BG_CARD = "#313244"
    FG_TITLE = "#89B4FA"
    FG_SUB = "#BAC2DE"
    FG_TEXT = "#CDD6F4"
    BTN_BG = "#89B4FA"
    BTN_FG = "#11111B"
    BTN_ACTIVE = "#B4BEFE"

    root.configure(bg=BG_MAIN)
    style = ttk.Style(root)
    style.theme_use("clam")

    # Configuração dos Estilos
    style.configure("Main.TFrame", background=BG_MAIN)
    style.configure("Title.TLabel", background=BG_MAIN, foreground=FG_TITLE, font=("Segoe UI", 24, "bold"))
    style.configure("Subtitle.TLabel", background=BG_MAIN, foreground=FG_SUB, font=("Segoe UI", 11))
    
    style.configure("Card.TFrame", background=BG_CARD)
    style.configure("CardTitle.TLabel", background=BG_CARD, foreground=FG_TITLE, font=("Segoe UI", 13, "bold"))
    style.configure("CardText.TLabel", background=BG_CARD, foreground=FG_TEXT, font=("Segoe UI", 10))
    
    style.configure("Action.TButton", font=("Segoe UI", 11, "bold"), background=BTN_BG, foreground=BTN_FG, borderwidth=0, padding=8)
    style.map("Action.TButton", background=[("active", BTN_ACTIVE)])
    
    style.configure("Status.TLabel", background=BG_MAIN, foreground=FG_SUB, font=("Segoe UI", 10, "italic"))
    style.configure("Footer.TLabel", background=BG_MAIN, foreground="#6C7086", font=("Segoe UI", 9))
    style.configure("Credit.TLabel", background=BG_MAIN, foreground="#F5E0DC", font=("Segoe UI", 10, "bold"))

    # Cabeçalho
    header = ttk.Frame(root, padding=(28, 24), style="Main.TFrame")
    header.pack(fill="x")
    ttk.Label(header, text="FIO Plot Automation", style="Title.TLabel").pack(anchor="w", fill="x")
    ttk.Label(header, text="Analise resultados de benchmark com rapidez e precisão", style="Subtitle.TLabel").pack(anchor="w", fill="x")

    # Corpo
    body = ttk.Frame(root, padding=28, style="Main.TFrame")
    body.pack(fill="both", expand=True)

    cards = [
        ("Comparação 2D", "Compare duas ou mais pastas de benchmark usando os arquivos JSON.", gui_chart_compare),
        ("Gráfico de Linha", "Visualize IOPS, banda ou latência ao longo do tempo através dos logs.", gui_chart_log),
        ("Histograma de Latência", "Analise a distribuição estatística dos tempos de resposta usando JSON.", gui_chart_histogram),
    ]
    
    for title, description, plotter in cards:
        card = ttk.Frame(body, padding=16, style="Card.TFrame")
        card.pack(fill="x", pady=8)
        
        content = ttk.Frame(card, style="Card.TFrame")
        content.pack(side="left", fill="x", expand=True)
        
        ttk.Label(content, text=title, style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(content, text=description, style="CardText.TLabel").pack(anchor="w", pady=(4, 0))
        
        ttk.Button(card, text="Selecionar Pastas", style="Action.TButton", cursor="hand2",
                   command=lambda p=plotter: launch_gui_plot(p, status)).pack(side="right", padx=(14, 0))

    status = ttk.Label(body, text="✓ Sistema pronto para análise.", style="Status.TLabel")
    status.pack(anchor="w", pady=(18, 0))
    
    # Rodapé com Créditos
    footer = ttk.Frame(root, padding=(28, 10), style="Main.TFrame")
    footer.pack(side="bottom", fill="x")
    
    ttk.Label(footer, text="Criado por: Gabriel Souza e Bruno Costa", style="Credit.TLabel").pack(anchor="center")
    ttk.Label(footer, text="Projeto da disciplina de Organização e Recuperação da Informação\nProfessor Orientador: Sérgio Fred Ribeiro Andrade", 
              style="Footer.TLabel", justify="center").pack(anchor="center", pady=(4,0))
    
    root.mainloop()


# ========================
# Menu Principal (Terminal)
# ========================

def main():
    while True:
        clear_screen()
        width = 66
        print("╔" + "═" * (width - 2) + "╗")
        print("║" + "   FIO PLOT AUTOMATION".center(width - 2) + "║")
        print("║" + "   Criado por: Gabriel Souza e Bruno Costa".center(width - 2) + "║")
        print("║" + "   Disciplina: Organização e Recuperação da Informação".center(width - 2) + "║")
        print("║" + "   Professor: Sérgio Fred Ribeiro Andrade".center(width - 2) + "║")
        print("╠" + "═" * (width - 2) + "╣")
        print("║" + "  [1] Comparar resultados de benchmark (2D)".ljust(width - 2) + "║")
        print("║" + "      (múltiplas pastas · JSON)".ljust(width - 2) + "║")
        print("║" + "  [2] Gráfico de linha (logs *.N.log)".ljust(width - 2) + "║")
        print("║" + "  [3] Histograma de latência (JSON)".ljust(width - 2) + "║")
        print("╠" + "═" * (width - 2) + "╣")
        print("║" + "  [0] Sair".ljust(width - 2) + "║")
        print("╚" + "═" * (width - 2) + "╝")

        choice = input("\n  Escolha uma opção > ").strip()

        if choice == "0":
            print("\n  Até logo!")
            sys.exit(0)
        elif choice == "1":
            settings = build_base_settings()
            run_plot(settings, chart_compare)
        elif choice == "2":
            settings = build_base_settings()
            run_plot(settings, chart_log)
        elif choice == "3":
            settings = build_base_settings()
            run_plot(settings, chart_histogram)
        else:
            print("\n  Opção inválida.")
            pause()


if __name__ == "__main__":
    try:
        main_gui()
    finally:
        shutil.rmtree(TMP_ROOT, ignore_errors=True)