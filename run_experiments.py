#!/usr/bin/env python3
"""
run_experiments.py

Batch experiment runner.
- All model binaries are compiled on startup.
- Each binary receives the path to experiments.toml and the experiment
  name directly - it reads its own parameters from the file.
- experiments.toml is completely unchanged.

Usage:
  python run_experiments.py
  python run_experiments.py --dry-run
  python run_experiments.py --experiments 1 3
  python run_experiments.py --models 1D 2D_polar
  python run_experiments.py --skip-compile
"""

import os
import sys
import subprocess
import shutil
import argparse
from pathlib import Path
from datetime import datetime
import json
import traceback
import re

try:
    import toml
except ImportError:
    print("Installing required package: toml")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "toml"])
    import toml


class ExperimentRunner:

    MODEL_EXECUTABLES = {
        "1D":             "bin/1d.exe"         if os.name == "nt" else "bin/1d",
        "2D_polar":       "bin/top.exe"        if os.name == "nt" else "bin/top",
        "2D_cylindrical": "bin/side.exe"       if os.name == "nt" else "bin/side",
        "2D_combined":    "bin/coupled_2d.exe" if os.name == "nt" else "bin/coupled_2d",
        "3D":             "bin/3d.exe"         if os.name == "nt" else "bin/3d",
    }

    MODEL_SOURCE_FILES = {
        "1D":             "1D.cpp",
        "2D_polar":       "2Dtop.cpp",
        "2D_cylindrical": "2Dside.cpp",
        "2D_combined":    "2Dcombined.cpp",
        "3D":             "3D.cpp",
    }

    MODEL_IC_FILES = {
        "1D":             "ic/ic_1d.dat",
        "2D_polar":       "ic/ic_polar.dat",
        "2D_cylindrical": "ic/ic_cyl.dat",
        "2D_combined":    ["ic/ic_polar.dat", "ic/ic_cyl.dat"],
        "3D":             "ic/master_ic.dat",
    }

    def __init__(self, experiments_file="experiments.toml",
                 results_root_dir="experiment_results"):
        self.experiments_file = str(Path(experiments_file).resolve())
        self.results_root_dir = Path(results_root_dir)
        self.results_root_dir.mkdir(parents=True, exist_ok=True)
        Path("bin").mkdir(exist_ok=True)
        Path("ic").mkdir(exist_ok=True)

    def _next_run_dir(self) -> Path:
        run_re = re.compile(r"^run(\d+)$", re.IGNORECASE)
        max_n = 0
        for p in self.results_root_dir.iterdir():
            if p.is_dir():
                m = run_re.match(p.name)
                if m:
                    try: max_n = max(max_n, int(m.group(1)))
                    except ValueError: pass
        return self.results_root_dir / f"run{max_n + 1:02d}"

    def create_run_folder(self, dry_run: bool) -> Path:
        run_dir = self._next_run_dir()
        if not dry_run:
            run_dir.mkdir(parents=True, exist_ok=False)
            meta = run_dir / "metadata"
            meta.mkdir(exist_ok=True)
            with open(meta / "run_info.json", "w") as f:
                json.dump({"created_at": datetime.now().isoformat(),
                           "experiments_file": self.experiments_file},
                          f, indent=2)
        return run_dir

    def load_experiments(self):
        if not os.path.exists(self.experiments_file):
            raise FileNotFoundError(f"Experiments file not found: {self.experiments_file}")
        with open(self.experiments_file, "r") as f:
            config = toml.load(f)
        experiments = config.get("experiment", [])
        if not experiments:
            raise ValueError("No experiments defined in config file")
        return experiments

    def compile_model(self, model_name: str) -> bool:
        print(f"  Compiling {model_name}...")
        build_targets = {
            "1D": "1d", "2D_polar": "top", "2D_cylindrical": "side",
            "2D_combined": "coupled", "3D": "3d",
        }
        target = build_targets.get(model_name)
        if not target:
            raise ValueError(f"Unknown model: {model_name}")

        if os.name == "nt":
            cmd = ["build.bat", target]
        else:
            source = self.MODEL_SOURCE_FILES[model_name]
            output = self.MODEL_EXECUTABLES[model_name]
            flags = ["-O3", "-march=native", "-std=c++17", "-fopenmp", "-ffast-math", "-funroll-loops"]
            cmd = ["g++"] + flags + ["-o", output, source, "writer.cpp", "initialConditions.cpp"]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                print(f"  ✗ Compilation failed for {model_name}\n{result.stderr}")
                return False
            print(f"  ✓ Compiled {model_name}")
            return True
        except subprocess.TimeoutExpired:
            print(f"  ✗ Compilation timeout for {model_name}")
            return False
        except Exception as e:
            print(f"  ✗ Compilation error for {model_name}: {e}")
            return False

    def compile_all(self, models: list) -> dict:
        print("\n" + "=" * 70)
        print("COMPILATION PHASE  (runs once for all experiments)")
        print("=" * 70)
        results = {m: self.compile_model(m) for m in models}
        ok  = [m for m, v in results.items() if v]
        bad = [m for m, v in results.items() if not v]
        print(f"\nCompilation: {len(ok)}/{len(results)} succeeded")
        if bad:
            print(f"  Failed: {', '.join(bad)}")
        print("=" * 70 + "\n")
        return results

    def run_model(self, model_name: str, exp_name: str,
                  exp_dir: Path, logs_dir: Path,
                  timeout=14400, keep_work=False) -> bool:

        exe = self.MODEL_EXECUTABLES.get(model_name)
        if not exe:
            print(f"  ✗ Unknown model: {model_name}")
            return False
        exe_path = Path(exe).resolve()
        if not exe_path.exists():
            print(f"  ✗ Executable not found: {exe_path}")
            return False

        (exp_dir / "results").mkdir(parents=True, exist_ok=True)
        (exp_dir / "spatiotemporal").mkdir(parents=True, exist_ok=True)

        work_root = exp_dir / "metadata" / "_work"
        work_root.mkdir(parents=True, exist_ok=True)
        work_dir = work_root / f"{model_name}_{datetime.now().strftime('%H%M%S')}"
        work_dir.mkdir(parents=True, exist_ok=True)
        (work_dir / "results").mkdir(exist_ok=True)

        # Command: exe  experiments.toml  exp_name  [ic_file ...]
        # The binary reads its parameters directly from the toml
        cmd = [str(exe_path), self.experiments_file, exp_name]

        ic_files = self.MODEL_IC_FILES.get(model_name)
        if ic_files:
            paths = ic_files if isinstance(ic_files, list) else [ic_files]
            for icf in paths:
                p = Path(icf).resolve()
                if p.exists():
                    cmd.append(str(p))

        print(f"  Running {model_name}...")

        start_time = datetime.now()
        try:
            result = subprocess.run(cmd, capture_output=True, text=True,
                                    timeout=timeout, cwd=str(work_dir))
            end_time = datetime.now()
            elapsed = (end_time - start_time).total_seconds()

            log_file = logs_dir / f"{model_name}_output.log"
            with open(log_file, "w") as f:
                f.write(f"=== {model_name} Simulation Log ===\n")
                f.write(f"Start:   {start_time}\nEnd:     {end_time}\n")
                f.write(f"Elapsed: {elapsed:.1f}s\nCWD:     {work_dir}\n")
                f.write(f"Command: {' '.join(cmd)}\n\n")
                f.write("=== STDOUT ===\n"); f.write(result.stdout or "")
                f.write("\n=== STDERR ===\n"); f.write(result.stderr or "")

            if result.returncode != 0:
                print(f"  ✗ Simulation failed for {model_name}")
                print((result.stderr or "")[:500])
                if not keep_work:
                    shutil.rmtree(work_dir, ignore_errors=True)
                return False

            print(f"  ✓ Completed {model_name} in {elapsed:.1f}s")
            moved = self._move_and_split_results(
                work_dir / "results", exp_dir / "results", exp_dir / "spatiotemporal")
            if moved == 0:
                print("    Warning: no output files found in work results/")
            if not keep_work:
                shutil.rmtree(work_dir, ignore_errors=True)
            return True

        except subprocess.TimeoutExpired:
            print(f"  ✗ Timeout for {model_name} (>{timeout}s)")
            if not keep_work:
                shutil.rmtree(work_dir, ignore_errors=True)
            return False
        except Exception as e:
            print(f"  ✗ Error for {model_name}: {e}")
            traceback.print_exc()
            if not keep_work:
                shutil.rmtree(work_dir, ignore_errors=True)
            return False

    def _move_and_split_results(self, raw: Path, results_dest: Path, st_dest: Path) -> int:
        if not raw.exists():
            return 0
        moved = 0
        for p in raw.iterdir():
            if not p.is_file():
                continue
            dest_dir = st_dest if "spatiotemporal" in p.name.lower() else results_dest
            dest = dest_dir / p.name
            if dest.exists():
                stem, suf = dest.stem, dest.suffix
                k = 2
                while True:
                    cand = dest_dir / f"{stem}__{k}{suf}"
                    if not cand.exists():
                        dest = cand
                        break
                    k += 1
            try:
                shutil.move(str(p), str(dest))
                moved += 1
            except Exception as e:
                print(f"    Warning: Could not move {p.name}: {e}")
        return moved

    def run_experiment(self, exp_id: int, experiment: dict,
                       run_dir: Path, compiled: dict,
                       dry_run=False, models_filter=None):
        exp_name = experiment.get("name", f"experiment_{exp_id}")
        description = experiment.get("description", "No description")

        print(f"\n{'=' * 70}")
        print(f"EXPERIMENT {exp_id}: {exp_name}")
        print(f"{'=' * 70}")
        print(f"Description: {description}")
        print("Parameters:")
        for key in ["D_U", "D_W", "CHI", "ALPHA", "BETA", "GAMMA", "W_0", "T_FINAL"]:
            if key in experiment:
                print(f"  {key} = {experiment[key]}")

        models_to_run = experiment.get("models", list(self.MODEL_EXECUTABLES.keys()))
        if models_filter:
            models_to_run = [m for m in models_to_run if m in models_filter]

        if dry_run:
            print("  [DRY RUN - would run:]")
            for model in models_to_run:
                status = "✓" if compiled.get(model) else "✗ (compilation failed)"
                print(f"    - {model}  {status}")
            return True

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        exp_dir   = run_dir / f"{timestamp}_{exp_name}"
        exp_dir.mkdir(parents=True, exist_ok=True)
        (exp_dir / "results").mkdir(exist_ok=True)
        (exp_dir / "spatiotemporal").mkdir(exist_ok=True)
        meta_dir = exp_dir / "metadata"
        logs_dir = meta_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        print(f"Output directory: {exp_dir}")
        with open(meta_dir / "experiment_config.json", "w") as f:
            json.dump(experiment, f, indent=2)

        print(f"\nModels to run: {', '.join(models_to_run)}")
        results = {"experiment_id": exp_id, "experiment_name": exp_name,
                   "timestamp": timestamp, "parameters": experiment, "models": {}}

        for model_name in models_to_run:
            print(f"\n--- {model_name} ---")
            if not compiled.get(model_name):
                print(f"  ✗ Skipping {model_name}: compilation failed earlier")
                results["models"][model_name] = {"status": "compilation_failed"}
                continue
            
            success = self.run_model(model_name, exp_name, exp_dir, logs_dir,
                                     timeout=14400, keep_work=False)
            results["models"][model_name] = {
                "status": "success" if success else "failed",
                "timestamp": datetime.now().isoformat(),
            }

        with open(meta_dir / "experiment_summary.json", "w") as f:
            json.dump(results, f, indent=2)

        successes = sum(1 for r in results["models"].values() if r["status"] == "success")
        total = len(results["models"])
        print(f"\n{'=' * 70}")
        print(f"EXPERIMENT {exp_id} COMPLETE: {successes}/{total} models succeeded")
        print(f"Results saved to: {exp_dir}")
        print(f"{'=' * 70}")
        return successes == total

    def run_all(self, dry_run=False, exp_filter=None,
                models_filter=None, skip_compile=False):

        experiments = self.load_experiments()
        run_dir = self.create_run_folder(dry_run=dry_run)

        needed_models = set()
        for idx, exp in enumerate(experiments, 1):
            if exp_filter and idx not in exp_filter:
                continue
            models = exp.get("models", list(self.MODEL_EXECUTABLES.keys()))
            if models_filter:
                models = [m for m in models if m in models_filter]
            needed_models.update(models)

        if skip_compile:
            print("--skip-compile: reusing existing binaries.")
            compiled = {m: Path(self.MODEL_EXECUTABLES[m]).exists() for m in needed_models}
        else:
            compiled = self.compile_all(list(needed_models))

        print(f"\n{'#' * 70}")
        print("# BATCH EXPERIMENT RUNNER")
        print(f"# Total experiments: {len(experiments)}")
        print(f"# Config: {self.experiments_file}")
        print(f"# This run: {run_dir}")
        if dry_run:
            print("# MODE: DRY RUN")
        print(f"{'#' * 70}")

        results_summary = []
        for idx, experiment in enumerate(experiments, 1):
            if exp_filter and idx not in exp_filter:
                continue
            try:
                success = self.run_experiment(idx, experiment, run_dir, compiled,
                                              dry_run, models_filter)
                results_summary.append({"id": idx,
                                        "name": experiment.get("name", f"exp_{idx}"),
                                        "success": success})
            except Exception as e:
                print(f"\n✗ EXPERIMENT {idx} CRASHED: {e}")
                traceback.print_exc()
                results_summary.append({"id": idx,
                                        "name": experiment.get("name", f"exp_{idx}"),
                                        "success": False, "error": str(e)})

        print(f"\n\n{'#' * 70}\n# FINAL SUMMARY\n{'#' * 70}")
        for r in results_summary:
            status = "✓" if r["success"] else "✗"
            error  = f" ({r.get('error', 'failed')})" if not r["success"] else ""
            print(f"{status} Experiment {r['id']}: {r['name']}{error}")

        total_success = sum(1 for r in results_summary if r["success"])
        print(f"\nTotal: {total_success}/{len(results_summary)} experiments successful")
        print(f"Run folder: {run_dir}\n{'#' * 70}\n")

        if not dry_run:
            meta = run_dir / "metadata"
            meta.mkdir(exist_ok=True)
            with open(meta / "run_summary.json", "w") as f:
                json.dump({"completed_at": datetime.now().isoformat(),
                           "run_dir": str(run_dir),
                           "results_summary": results_summary,
                           "total_experiments": len(results_summary),
                           "successful_experiments": total_success}, f, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Run batch simulation experiments (compile once, run many)")
    parser.add_argument("--experiments", "-e", nargs="+", type=int,
                        help="Experiment IDs to run (default: all)")
    parser.add_argument("--models", "-m", nargs="+",
                        choices=["1D", "2D_polar", "2D_cylindrical", "2D_combined", "3D"],
                        help="Specific models to run (default: all)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be run without executing")
    parser.add_argument("--skip-compile", action="store_true",
                        help="Skip compilation and reuse existing binaries in bin/")
    parser.add_argument("--config", "-c", default="experiments.toml",
                        help="Path to experiments config")
    parser.add_argument("--output-dir", "-o", default="experiment_results",
                        help="Root directory for runs")
    args = parser.parse_args()

    runner = ExperimentRunner(experiments_file=args.config,
                              results_root_dir=args.output_dir)
    runner.run_all(dry_run=args.dry_run, exp_filter=args.experiments,
                   models_filter=args.models, skip_compile=args.skip_compile)


if __name__ == "__main__":
    main()