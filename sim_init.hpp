#ifndef SIM_INIT_HPP
#define SIM_INIT_HPP
 
#include "constants.hpp"
 
#include <string>
#include <fstream>
#include <iostream>
#include <cstdlib>
 
struct SimParams {
    double D_U = ::D_U;
    double D_W = ::D_W;
    double CHI = ::CHI;
    double ALPHA = ::ALPHA;
    double BETA = ::BETA;
    double GAMMA = ::GAMMA;
    double W_0 = ::W_0;
    double T_FINAL = ::T_FINAL;
 
    std::string ic_file;
    std::string ic_file2;
 
    static SimParams load(const std::string& toml_path,
                          const std::string& exp_name,
                          int argc, char* argv[]) {
        SimParams p;
 
        // IC paths from remaining positional args (argv[3], argv[4])
        if (argc > 3) p.ic_file  = argv[3];
        if (argc > 4) p.ic_file2 = argv[4];
 
        std::ifstream f(toml_path);
        if (!f.is_open()) {
            std::cerr << "[sim_init] ERROR: cannot open " << toml_path
                      << " - using constants.hpp defaults.\n";
            return p;
        }
 
        // ---- finding the right [[experiment]] block ----
        bool in_block = false;
        std::string line;
 
        while (std::getline(f, line)) {
            auto hash = line.find('#');
            if (hash != std::string::npos)
                line = line.substr(0, hash);
 
            auto ltrim = line.find_first_not_of(" \t\r\n");
            auto rtrim = line.find_last_not_of(" \t\r\n");
            if (ltrim == std::string::npos) { // blank after stripping
                continue;
            }
            line = line.substr(ltrim, rtrim - ltrim + 1);
 
            if (line == "[[experiment]]") {
                if (in_block) break;
                std::string peek;
                while (std::getline(f, peek)) {
                    auto h2 = peek.find('#');
                    if (h2 != std::string::npos) peek = peek.substr(0, h2);
                    auto l2 = peek.find_first_not_of(" \t\r\n");
                    if (l2 == std::string::npos) continue;
                    peek = peek.substr(l2, peek.find_last_not_of(" \t\r\n") - l2 + 1);
 
                    if (peek.substr(0, 4) == "name") {
                        auto q1 = peek.find('"');
                        auto q2 = peek.rfind('"');
                        if (q1 != std::string::npos && q2 != q1) {
                            std::string found_name = peek.substr(q1 + 1, q2 - q1 - 1);
                            if (found_name == exp_name) {
                                in_block = true;
                            }
                        }
                        break;
                    }

                    if (peek == "[[experiment]]") break;
                }
                continue;
            }
 
            if (!in_block) continue;
 
            auto eq = line.find('=');
            if (eq == std::string::npos) continue;
 
            std::string key = line.substr(0, eq);
            auto ke = key.find_last_not_of(" \t");
            if (ke != std::string::npos) key = key.substr(0, ke + 1);
 
            std::string val_str = line.substr(eq + 1);
            auto vs = val_str.find_first_not_of(" \t");
            if (vs == std::string::npos) continue;
            val_str = val_str.substr(vs);
 
            if (val_str.front() == '"') continue;
 
            double val = std::atof(val_str.c_str());
 
            if      (key == "D_U")     p.D_U     = val;
            else if (key == "D_W")     p.D_W     = val;
            else if (key == "CHI")     p.CHI     = val;
            else if (key == "ALPHA")   p.ALPHA   = val;
            else if (key == "BETA")    p.BETA    = val;
            else if (key == "GAMMA")   p.GAMMA   = val;
            else if (key == "W_0")     p.W_0     = val;
            else if (key == "T_FINAL") p.T_FINAL = val;
            // unknown keys (description and etc.) are silently ignored
        }
 
        if (!in_block) {
            std::cerr << "[sim_init] WARNING: experiment \"" << exp_name
                      << "\" not found in " << toml_path
                      << " - using constants.hpp defaults.\n";
        }
 
        return p;
    }
 
    void print(const std::string& exp_name) const {
        std::cout << "[sim_init] Experiment: " << exp_name << "\n"
                  << "  D_U="   << D_U   << "  D_W="   << D_W   << "  CHI="    << CHI   << "\n"
                  << "  ALPHA=" << ALPHA << "  BETA="  << BETA  << "  GAMMA="  << GAMMA
                  << "  W_0="   << W_0   << "  T_FINAL=" << T_FINAL << "\n";
    }
};
 
#define SIM_INIT(argc, argv, DT, SAVE_EVERY_T)                                      \
    if ((argc) < 3) {                                                                \
        std::cerr << "[sim_init] Usage: " << (argv)[0]                              \
                  << " experiments.toml <exp_name> [ic_file] [ic_file2]\n";         \
        return 1;                                                                    \
    }                                                                                \
    const std::string _toml_path = (argv)[1];                                       \
    const std::string _exp_name = (argv)[2];                                       \
    SimParams _p = SimParams::load(_toml_path, _exp_name, (argc), (argv));          \
    _p.print(_exp_name);                                                             \
    const double D_U = _p.D_U;                                                   \
    const double D_W = _p.D_W;                                                   \
    const double CHI = _p.CHI;                                                   \
    const double ALPHA = _p.ALPHA;                                                 \
    const double BETA = _p.BETA;                                                  \
    const double GAMMA = _p.GAMMA;                                                 \
    const double W_0 = _p.W_0;                                                   \
    const double t_final = _p.T_FINAL;                                              \
    const int n_steps = static_cast<int>(t_final / (DT));                \
    const int save_interval = static_cast<int>((SAVE_EVERY_T) / (DT));         \
    const int progress_interval = static_cast<int>(PROGRESS_EVERY_T / (DT));       \
    const std::string ic_file = _p.ic_file;                                       \
    const std::string ic_file2 = _p.ic_file2
 
#endif // SIM_INIT_HPP