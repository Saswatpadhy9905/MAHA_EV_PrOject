import networkx as nx
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.animation as animation
from matplotlib.widgets import Button
from scipy.integrate import solve_ivp
import warnings
warnings.filterwarnings('ignore')

# ──────────────────────────────────────────────────────
#  PARAMETERS
# ──────────────────────────────────────────────────────
eta_EV  = 0.05
eta_NEV = 0.05
alpha   = 0.3
gamma   = 1.0
k_rep   = 10.0

LINK_CAP   = 0.5
LINK_STEEP = 1.0

T_FINAL       = 400.0
N_TIME_POINTS = 2000
SOLVER_RTOL   = 1e-5
SOLVER_ATOL   = 1e-7
MAX_STEP      = 2.0


# ──────────────────────────────────────────────────────
#  PIECEWISE PRICING
# ──────────────────────────────────────────────────────
def get_station_parameters(t, station_id):
    if station_id == 'S1':
        if   t < 100: return {'p_s': 0.50, 'mu_s': 1.5, 'c_s': 0.10, 'nu_s': 10.0}
        elif t < 200: return {'p_s': 0.50, 'mu_s': 1.5, 'c_s': 0.10, 'nu_s': 10.0}
        elif t < 300: return {'p_s': 0.42, 'mu_s': 2.5, 'c_s': 0.18, 'nu_s': 15.0}
        else:         return {'p_s': 0.45, 'mu_s': 2.5, 'c_s': 0.16, 'nu_s': 15.0}
    elif station_id == 'S2':
        if   t < 100: return {'p_s': 0.50, 'mu_s': 1.5, 'c_s': 0.10, 'nu_s': 10.0}
        elif t < 200: return {'p_s': 0.25, 'mu_s': 1.5, 'c_s': 0.10, 'nu_s': 10.0}
        elif t < 300: return {'p_s': 0.25, 'mu_s': 1.5, 'c_s': 0.14, 'nu_s': 10.0}
        else:         return {'p_s': 0.38, 'mu_s': 2.0, 'c_s': 0.20, 'nu_s': 13.0}
    return {'p_s': 0.5, 'mu_s': 1.5, 'c_s': 0.1, 'nu_s': 10.0}


# ──────────────────────────────────────────────────────
#  NETWORK CONSTRUCTION
#  Graph: O -> A -> D  (via S1 EV-only or mixed)
#         O -> B -> D  (via S2 EV-only or mixed)
#  Nodes: O, A, B, D
# ──────────────────────────────────────────────────────
def create_network():
    """
    Network topology (TC-7: 4-node, 2-station):
    ─────────────────────────────────────────────────
    O──road──A──mixed──D
    O──[S1]──A                (EV-only, S1 on O->A)
    O──road──B──mixed──D
    B──[S2]──D                (EV-only, S2 on B->D)
    A──road──B
    ─────────────────────────────────────────────────
    """
    G = nx.MultiDiGraph()

    for n in ['O', 'A', 'B', 'D']:
        G.add_node(n)

    # ---- Origin self-loop ----
    G.add_edge('O', 'O', key=0, link_type='origin', origin_id='O1', is_origin=True)

    # ---- O -> A  (mixed + EV-only S1) ----
    G.add_edge('O', 'A', key=0, link_type='mixed')
    G.add_edge('O', 'A', key=1, link_type='EV-only', station_id='S1')

    # ---- O -> B  (mixed) ----
    G.add_edge('O', 'B', key=0, link_type='mixed')

    # ---- A -> B  (mixed) ----
    G.add_edge('A', 'B', key=0, link_type='mixed')

    # ---- B -> D  (mixed + EV-only S2) ----
    G.add_edge('B', 'D', key=0, link_type='mixed')
    G.add_edge('B', 'D', key=1, link_type='EV-only', station_id='S2')

    # ---- A -> D  (mixed) ----
    G.add_edge('A', 'D', key=0, link_type='mixed')

    # ---- Destination self-loop ----
    G.add_edge('D', 'D', key=0, link_type='destination', dest_id='D1', is_destination=True)

    # ---- Assign link_id = enumerate-index ----
    edges_list = list(G.edges(keys=True))
    for idx, (u, v, k) in enumerate(edges_list):
        G[u][v][k]['link_id'] = idx

    idx_to_edge = edges_list
    edge_to_idx = {e: i for i, e in enumerate(edges_list)}

    origins, destinations = [], []
    charging_stations = {}
    for i, (u, v, k) in enumerate(edges_list):
        d = G[u][v][k]
        if d.get('is_origin'):
            origins.append(i)
        if d.get('is_destination'):
            destinations.append(i)
        if d.get('link_type') == 'EV-only':
            charging_stations[d['station_id']] = i

    pos = {
        'O': (0, 3),
        'A': (3, 6),
        'B': (3, 0),
        'D': (6, 3),
    }
    nx.set_node_attributes(G, pos, 'pos')

    return G, origins, destinations, charging_stations, idx_to_edge, edge_to_idx


# ──────────────────────────────────────────────────────
#  PATH ENUMERATION
# ──────────────────────────────────────────────────────
def enumerate_paths(G, origins, destinations, charging_stations, idx_to_edge, edge_to_idx):
    paths_EV  = {}
    paths_NEV = {}

    for o_idx in origins:
        u_o, v_o, k_o = idx_to_edge[o_idx]
        start = u_o

        for d_idx in destinations:
            u_d, v_d, k_d = idx_to_edge[d_idx]
            end = u_d

            od = (o_idx, d_idx)
            mixed, charging = [], []

            if nx.has_path(G, start, end):
                for path_edges in nx.all_simple_edge_paths(G, start, end):
                    if any(G[u][v][k].get('is_origin') or G[u][v][k].get('is_destination')
                           for u, v, k in path_edges):
                        continue

                    path_ids = ([o_idx]
                                + [edge_to_idx[(u, v, k)] for u, v, k in path_edges]
                                + [d_idx])

                    ev_cnt = sum(1 for lid in path_ids
                                 if G[idx_to_edge[lid][0]][idx_to_edge[lid][1]]
                                     [idx_to_edge[lid][2]].get('link_type') == 'EV-only')

                    if ev_cnt == 0:
                        mixed.append(path_ids)
                    elif ev_cnt == 1:
                        charging.append(path_ids)

            paths_NEV[od] = mixed
            paths_EV[od]  = mixed + charging if charging else mixed

    return paths_EV, paths_NEV


# ──────────────────────────────────────────────────────
#  OD DEMAND
# ──────────────────────────────────────────────────────
def create_od_demand(G, origins, destinations, idx_to_edge):
    origin_name_to_idx = {}
    dest_name_to_idx   = {}
    for i, (u, v, k) in enumerate(idx_to_edge):
        d = G[u][v][k]
        if d.get('is_origin'):
            origin_name_to_idx[d['origin_id']] = i
        if d.get('is_destination'):
            dest_name_to_idx[d['dest_id']] = i

    scenario = {
        'O1': {'total_flow': 1.0, 'beta_EV': 0.6, 'destinations': {'D1': 1.0}},
    }

    lambda_EV, lambda_NEV = {}, {}
    for oname, cfg in scenario.items():
        o_idx = origin_name_to_idx[oname]
        for dname, frac in cfg['destinations'].items():
            d_idx = dest_name_to_idx[dname]
            od    = (o_idx, d_idx)
            lambda_EV[od]  = cfg['total_flow'] * cfg['beta_EV']       * frac
            lambda_NEV[od] = cfg['total_flow'] * (1 - cfg['beta_EV']) * frac

    return lambda_EV, lambda_NEV


# ──────────────────────────────────────────────────────
#  OUTFLOW / LATENCY
# ──────────────────────────────────────────────────────
def outflow_fn(x, mu=None, nu=None, is_charging=False):
    x = max(float(x), 0.0)
    if is_charging and mu is not None and nu is not None:
        return mu * (1.0 - np.exp(-(nu / max(mu, 1e-9)) * x))
    return LINK_CAP * (1.0 - np.exp(-LINK_STEEP * x))


def latency_fn(x, is_charging=False):
    if is_charging:
        return 0.1
    f = outflow_fn(x)
    return 1.0 + 2.0 * (f / LINK_CAP) ** 4


# ──────────────────────────────────────────────────────
#  ROUTING MATRIX  (paper eq. 5)
# ──────────────────────────────────────────────────────
def compute_routing_matrix(y_EV, y_NEV,
                            paths_EV, paths_NEV,
                            od_pairs_EV, od_pairs_NEV,
                            n_links):
    pair_demand = {}

    def accumulate(od_pairs, paths_dict, y_vec):
        p_idx = 0
        for od in od_pairs:
            for path in paths_dict[od]:
                yp = float(y_vec[p_idx])
                for step in range(len(path) - 1):
                    j, i = path[step], path[step + 1]
                    pair_demand[(j, i)] = pair_demand.get((j, i), 0.0) + yp
                p_idx += 1

    accumulate(od_pairs_EV,  paths_EV,  y_EV)
    accumulate(od_pairs_NEV, paths_NEV, y_NEV)

    succ_sum = {}
    for (j, i), d in pair_demand.items():
        succ_sum[j] = succ_sum.get(j, 0.0) + d

    R = np.zeros((n_links, n_links))
    for (j, i), d in pair_demand.items():
        denom = succ_sum.get(j, 0.0)
        if denom > 1e-12:
            R[j, i] = d / denom
        else:
            succs = [ii for (jj, ii) in pair_demand if jj == j]
            R[j, i] = 1.0 / max(len(succs), 1)

    return R


# ──────────────────────────────────────────────────────
#  PATH COSTS
# ──────────────────────────────────────────────────────
def compute_path_costs(x, paths_dict, od_pairs, idx_to_edge, G, t, vcls='EV'):
    costs = []
    for od in od_pairs:
        for path in paths_dict[od]:
            cost = 0.0
            for lid in path:
                u, v, k = idx_to_edge[lid]
                d  = G[u][v][k]
                lt = d.get('link_type', 'mixed')
                if lt in ('origin', 'destination'):
                    continue
                elif lt == 'EV-only' and vcls == 'EV':
                    sid = d['station_id']
                    sp  = get_station_parameters(t, sid)
                    xi  = x[lid]
                    wt  = xi / max(sp['mu_s'], 1e-9)
                    cost += latency_fn(xi, True) + alpha * wt + gamma * sp['p_s']
                else:
                    cost += latency_fn(x[lid])
            costs.append(cost)
    return np.array(costs)


# ──────────────────────────────────────────────────────
#  COUPLED ODE
# ──────────────────────────────────────────────────────
def coupled_dynamics(t, state, params):
    n_links     = params['n_links']
    n_pEV       = params['n_paths_EV']
    G           = params['G']
    idx_to_edge = params['idx_to_edge']

    x     = state[:n_links]
    y_EV  = state[n_links:n_links + n_pEV]
    y_NEV = state[n_links + n_pEV:]

    # outflows
    f = np.zeros(n_links)
    for i in range(n_links):
        u, v, k = idx_to_edge[i]
        d  = G[u][v][k]
        lt = d.get('link_type', 'mixed')
        if lt == 'origin':
            f[i] = params['lambda_origin'][i]
        elif lt == 'EV-only':
            sp   = get_station_parameters(t, d['station_id'])
            f[i] = outflow_fn(x[i], mu=sp['mu_s'], nu=sp['nu_s'], is_charging=True)
        else:
            f[i] = outflow_fn(x[i])

    # routing matrix
    R = compute_routing_matrix(y_EV, y_NEV,
                               params['paths_EV'], params['paths_NEV'],
                               params['od_pairs_EV'], params['od_pairs_NEV'],
                               n_links)

    # link density: dx/dt = (R^T - I) f
    dx_dt = R.T @ f - f

    # replicator - EV
    tau_EV   = compute_path_costs(x, params['paths_EV'], params['od_pairs_EV'],
                                  idx_to_edge, G, t, 'EV')
    dy_EV_dt = np.zeros(n_pEV)
    idx = 0
    for od in params['od_pairs_EV']:
        np_od  = len(params['paths_EV'][od])
        lam    = params['lambda_od_EV'][od]
        y_od   = np.maximum(y_EV[idx:idx + np_od], 1e-9)
        total  = y_od.sum()
        y_od   = y_od * (lam / total) if total > 1e-12 else np.full(np_od, lam / np_od)
        if lam > 1e-9:
            tau_od  = tau_EV[idx:idx + np_od]
            tau_avg = (y_od * tau_od).sum() / lam
            for ii in range(np_od):
                dy_EV_dt[idx + ii] = k_rep * eta_EV * y_od[ii] * (tau_avg - tau_od[ii])
        idx += np_od

    # replicator - NEV
    tau_NEV   = compute_path_costs(x, params['paths_NEV'], params['od_pairs_NEV'],
                                   idx_to_edge, G, t, 'NEV')
    n_pNEV    = params['n_paths_NEV']
    dy_NEV_dt = np.zeros(n_pNEV)
    idx = 0
    for od in params['od_pairs_NEV']:
        np_od  = len(params['paths_NEV'][od])
        lam    = params['lambda_od_NEV'][od]
        y_od   = np.maximum(y_NEV[idx:idx + np_od], 1e-9)
        total  = y_od.sum()
        y_od   = y_od * (lam / total) if total > 1e-12 else np.full(np_od, lam / np_od)
        if lam > 1e-9:
            tau_od  = tau_NEV[idx:idx + np_od]
            tau_avg = (y_od * tau_od).sum() / lam
            for ii in range(np_od):
                dy_NEV_dt[idx + ii] = k_rep * eta_NEV * y_od[ii] * (tau_avg - tau_od[ii])
        idx += np_od

    return np.concatenate([dx_dt, dy_EV_dt, dy_NEV_dt])


# ──────────────────────────────────────────────────────
#  MAIN SIMULATION RUNNER
# ──────────────────────────────────────────────────────
def run_simulation():
    print("\n" + "=" * 70)
    print("EV CHARGING STATION COMPETITION SIMULATION  [TC-7]")
    print("=" * 70)

    (G, origins, destinations, charging_stations,
     idx_to_edge, edge_to_idx) = create_network()

    for i, (u, v, k) in enumerate(idx_to_edge):
        assert G[u][v][k]['link_id'] == i, f"link_id mismatch at index {i}"
    print("CHECK: link_id == enum_idx  PASSED")

    paths_EV, paths_NEV = enumerate_paths(
        G, origins, destinations, charging_stations, idx_to_edge, edge_to_idx)
    lambda_EV, lambda_NEV = create_od_demand(
        G, origins, destinations, idx_to_edge)

    n_links = len(idx_to_edge)
    print(f"Network: {n_links} links,  {len(charging_stations)} stations")
    print(f"origins={origins}  destinations={destinations}")
    print(f"charging_stations={charging_stations}")

    def od_name(od):
        u0, v0, k0 = idx_to_edge[od[0]]
        u1, v1, k1 = idx_to_edge[od[1]]
        on = G[u0][v0][k0].get('origin_id', u0)
        dn = G[u1][v1][k1].get('dest_id',   u1)
        return f"{on}->{dn}"

    od_pairs_EV, y_EV_0   = [], []
    od_pairs_NEV, y_NEV_0 = [], []

    for od in sorted(lambda_EV.keys()):
        lam = lambda_EV[od]
        if lam > 1e-9 and od in paths_EV and len(paths_EV[od]) > 0:
            od_pairs_EV.append(od)
            np_od = len(paths_EV[od])
            y_EV_0.extend([lam / np_od] * np_od)

    for od in sorted(lambda_NEV.keys()):
        lam = lambda_NEV[od]
        if lam > 1e-9 and od in paths_NEV and len(paths_NEV[od]) > 0:
            od_pairs_NEV.append(od)
            np_od = len(paths_NEV[od])
            y_NEV_0.extend([lam / np_od] * np_od)

    print("\nActive EV OD pairs:")
    for od in od_pairs_EV:
        print(f"  {od_name(od)}  lambda={lambda_EV[od]:.3f}  "
              f"n_paths={len(paths_EV[od])}")
    print("Active NEV OD pairs:")
    for od in od_pairs_NEV:
        print(f"  {od_name(od)}  lambda={lambda_NEV[od]:.3f}  "
              f"n_paths={len(paths_NEV[od])}")

    x0     = np.zeros(n_links)
    state0 = np.concatenate([x0, y_EV_0, y_NEV_0])
    n_paths_EV  = len(y_EV_0)
    n_paths_NEV = len(y_NEV_0)

    print(f"\nState dim: {len(state0)} = {n_links} links "
          f"+ {n_paths_EV} EV paths + {n_paths_NEV} NEV paths")

    lambda_origin = np.zeros(n_links)
    for o_idx in origins:
        lam = (sum(lambda_EV.get((o_idx, d), 0.0)  for d in destinations) +
               sum(lambda_NEV.get((o_idx, d), 0.0) for d in destinations))
        lambda_origin[o_idx] = lam
    print(f"Origin outflows: { {i: lambda_origin[i] for i in origins} }")

    params = dict(
        n_links=n_links, n_paths_EV=n_paths_EV, n_paths_NEV=n_paths_NEV,
        paths_EV=paths_EV, paths_NEV=paths_NEV,
        od_pairs_EV=od_pairs_EV, od_pairs_NEV=od_pairs_NEV,
        lambda_od_EV=lambda_EV, lambda_od_NEV=lambda_NEV,
        lambda_origin=lambda_origin,
        charging_stations=charging_stations,
        G=G, idx_to_edge=idx_to_edge,
    )

    # Exploration floor at phase transitions (bounded rationality)
    MU_EXPLORE = 0.02

    def apply_exploration_floor(state, od_pairs_EV, od_pairs_NEV,
                                paths_EV, paths_NEV, lambda_EV, lambda_NEV,
                                n_links, n_paths_EV):
        x_s  = np.maximum(state[:n_links], 0.0)
        yEV  = state[n_links: n_links + n_paths_EV].copy()
        yNEV = state[n_links + n_paths_EV:].copy()

        def floor_reset(y_vec, od_pairs, paths_dict, lam_dict):
            idx = 0
            for od in od_pairs:
                np_od = len(paths_dict[od])
                lam   = lam_dict[od]
                floor = MU_EXPLORE * lam / np_od
                y_od  = np.maximum(y_vec[idx:idx + np_od], floor)
                total = y_od.sum()
                y_vec[idx:idx + np_od] = y_od * (lam / total)
                idx  += np_od
            return y_vec

        yEV  = floor_reset(yEV,  od_pairs_EV,  paths_EV,  lambda_EV)
        yNEV = floor_reset(yNEV, od_pairs_NEV, paths_NEV, lambda_NEV)
        return np.concatenate([x_s, yEV, yNEV])

    phase_bounds  = [0, 100, 200, 300, T_FINAL]
    t_all = x_all = y_EV_all = y_NEV_all = None
    current_state = state0.copy()

    for ph in range(len(phase_bounds) - 1):
        t0, t1 = phase_bounds[ph], phase_bounds[ph + 1]
        n_pts  = max(50, int(N_TIME_POINTS * (t1 - t0) / T_FINAL))
        t_eval = np.linspace(t0, t1, n_pts)

        current_state = apply_exploration_floor(
            current_state, od_pairs_EV, od_pairs_NEV,
            paths_EV, paths_NEV, lambda_EV, lambda_NEV,
            n_links, n_paths_EV)

        print(f"  Phase {ph + 1}: t in [{t0}, {t1}]", end='', flush=True)
        sol = solve_ivp(lambda t, s: coupled_dynamics(t, s, params),
                        [t0, t1], current_state,
                        method='Radau', t_eval=t_eval,
                        rtol=SOLVER_RTOL, atol=SOLVER_ATOL, max_step=MAX_STEP)
        ok = "OK" if sol.success else f"WARN: {sol.message}"
        print(f"  {ok}  ({len(sol.t)} pts)")

        sol.y[:n_links, :] = np.maximum(sol.y[:n_links, :], 0.0)

        xp    = sol.y[:n_links, :]
        yEVp  = sol.y[n_links:n_links + n_paths_EV, :]
        yNEVp = sol.y[n_links + n_paths_EV:, :]

        if ph == 0:
            t_all, x_all, y_EV_all, y_NEV_all = sol.t, xp, yEVp, yNEVp
        else:
            t_all     = np.concatenate([t_all,     sol.t[1:]])
            x_all     = np.concatenate([x_all,     xp[:,     1:]], axis=1)
            y_EV_all  = np.concatenate([y_EV_all,  yEVp[:,   1:]], axis=1)
            y_NEV_all = np.concatenate([y_NEV_all, yNEVp[:,  1:]], axis=1)

        current_state = sol.y[:, -1]
        current_state[:n_links] = np.maximum(current_state[:n_links], 0.0)

    print(f"Total trajectory: {len(t_all)} pts")

    # Station metrics
    q_s, p_s = {}, {}
    for sid, lid in charging_stations.items():
        q_s[sid] = np.array([
            outflow_fn(x_all[lid, i],
                       mu=get_station_parameters(t_all[i], sid)['mu_s'],
                       nu=get_station_parameters(t_all[i], sid)['nu_s'],
                       is_charging=True)
            for i in range(len(t_all))])
        p_s[sid] = np.array([
            get_station_parameters(t_all[i], sid)['p_s']
            for i in range(len(t_all))])

    print("\nStation queue means per phase:")
    for sid, lid in charging_stations.items():
        for _, ts, te in [('P1', 0, 100), ('P2', 100, 200), ('P3', 200, 300), ('P4', 300, 400)]:
            mask = (t_all >= ts) & (t_all <= te)
            print(f"  {sid} q_mean[{ts}-{te}] = {q_s[sid][mask].mean():.4f}")

    print("\n--- Figure 1: Interactive Animation ---")
    create_network_animation(
        G, x_all, y_EV_all, y_NEV_all, t_all, idx_to_edge,
        charging_stations, paths_EV, paths_NEV,
        od_pairs_EV, od_pairs_NEV, lambda_EV, lambda_NEV)

    print("--- Figure 2: Path Demand Dynamics ---")
    plot_path_demands(
        t_all, y_EV_all, y_NEV_all,
        paths_EV, paths_NEV,
        od_pairs_EV, od_pairs_NEV,
        lambda_EV, lambda_NEV, G, idx_to_edge)

    print("--- Figure 3: Replicator Convergence ---")
    plot_cost_convergence(
        t_all, x_all, y_EV_all, y_NEV_all,
        paths_EV, paths_NEV,
        od_pairs_EV, od_pairs_NEV,
        lambda_EV, lambda_NEV, idx_to_edge, G)

    print("--- Figure 4: Competition Metrics ---")
    plot_charging_station_metrics(q_s, p_s, t_all, charging_stations, x_all)


# ══════════════════════════════════════════════════════
#  FIGURE 1 – INTERACTIVE NETWORK ANIMATION
# ══════════════════════════════════════════════════════
def create_network_animation(G, x_all, y_EV_all, y_NEV_all,
                              t_all, idx_to_edge, charging_stations,
                              paths_EV, paths_NEV,
                              od_pairs_EV, od_pairs_NEV, lambda_EV, lambda_NEV):
    n_links = x_all.shape[0]
    n_t     = x_all.shape[1]

    # Pre-compute per-link demand trajectory
    link_demand = np.zeros((n_links, n_t))
    def acc_demand(od_pairs, paths_dict, y_arr):
        p_idx = 0
        for od in od_pairs:
            for path in paths_dict[od]:
                for lid in path:
                    link_demand[lid] += y_arr[p_idx]
                p_idx += 1
    acc_demand(od_pairs_EV,  paths_EV,  y_EV_all)
    acc_demand(od_pairs_NEV, paths_NEV, y_NEV_all)

    # Mutable position dict for dragging
    pos = {n: list(xy) for n, xy in nx.get_node_attributes(G, 'pos').items()}

    fig = plt.figure(figsize=(16, 9))
    fig.patch.set_facecolor('#f0f4f8')
    ax_net  = fig.add_axes([0.01, 0.12, 0.69, 0.84])
    ax_info = fig.add_axes([0.72, 0.12, 0.27, 0.84])

    edges_list   = list(G.edges(keys=True, data=True))
    parallel_map = {}
    for u, v, k, d in edges_list:
        parallel_map.setdefault((u, v), []).append(k)

    state     = {'frame': 0, 'selected_link': None}
    anim_obj  = [None]

    node_style = {
        'O': ('#2980b9', 'white'),
        'D': ('#e74c3c', 'white'),
    }

    def link_color(ltype):
        return {'EV-only': '#27ae60'}.get(ltype, '#2c3e50')

    # ---------- DRAW ----------
    def draw_frame(frame):
        ax_net.clear()
        ax_net.set_xlim(-1, 8); ax_net.set_ylim(-1, 8)
        ax_net.axis('off'); ax_net.set_facecolor('#f8f9fa')
        fig.suptitle(f'Network Simulation   t = {t_all[frame]:.1f} s',
                     fontsize=15, fontweight='bold', y=0.975, color='#1a202c')

        for u, v, k, edata in edges_list:
            if u == v: continue
            lid   = edata['link_id']
            ltype = edata.get('link_type', 'mixed')
            base_c = link_color(ltype)
            ls    = 'dashed' if ltype == 'EV-only' else 'solid'

            x1, y1 = pos[u]; x2, y2 = pos[v]
            par_keys = parallel_map.get((u, v), [])
            n_par    = len(par_keys)
            idx_par  = par_keys.index(k) if k in par_keys else 0
            rad = (+0.28 if idx_par == 0 else -0.28) if n_par > 1 else 0.0

            x_val = max(float(x_all[lid, frame]), 0)
            lw    = 1.5 + x_val * 3.5
            dim   = 1.0 if (state['selected_link'] is None
                            or state['selected_link'] == lid) else 0.28

            ax_net.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=base_c,
                                lw=lw, linestyle=ls,
                                connectionstyle=f"arc3,rad={rad}",
                                shrinkA=17, shrinkB=17, alpha=dim))

            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            dx, dy = x2 - x1, y2 - y1
            nm    = max(np.hypot(dx, dy), 1e-9)
            px, py = -dy / nm, dx / nm
            sign  = +1 if idx_par == 0 else -1
            off   = 0.30 if n_par <= 1 else 0.55
            lx    = mx + px * off * sign
            ly    = my + py * off * sign

            if ltype == 'EV-only':
                lbl = edata.get('station_id', '')
                fc  = '#d5f5e3'
            else:
                lbl = f'L{lid}'
                fc  = 'white'

            hl   = (state['selected_link'] == lid)
            ec_b = '#e74c3c' if hl else base_c
            ax_net.text(lx, ly, lbl, fontsize=7, ha='center', va='center',
                        color=base_c, fontweight='bold',
                        bbox=dict(boxstyle='round,pad=0.15', fc=fc,
                                  ec=ec_b, alpha=0.9, lw=1.5 if hl else 0.8))

        for node in G.nodes():
            nx_, ny_ = pos[node]
            fc, tc  = node_style.get(node, ('#ecf0f1', '#2c3e50'))
            ax_net.add_patch(
                plt.Circle((nx_, ny_), 0.4, color=fc, ec='#1a202c', lw=2, zorder=5))
            ax_net.text(nx_, ny_, node, ha='center', va='center',
                        fontsize=9, fontweight='bold', zorder=6, color=tc)

        ax_net.legend(handles=[
            mpatches.Patch(color='#2c3e50', label='Mixed link'),
            mpatches.Patch(color='#27ae60', label='EV-only link (charging)'),
            mpatches.Patch(color='#2980b9', label='Origin node'),
            mpatches.Patch(color='#e74c3c', label='Destination node'),
        ], loc='lower left', fontsize=9, framealpha=0.95, edgecolor='#cbd5e1')

        render_info(frame)
        fig.canvas.draw_idle()

    # ---------- INFO PANEL ----------
    def render_info(frame):
        ax_info.clear()
        ax_info.axis('off')
        ax_info.set_facecolor('#f8fafc')
        for sp in ax_info.spines.values():
            sp.set_color('#cbd5e1'); sp.set_linewidth(1.5)

        t_now = t_all[frame]
        lid   = state['selected_link']

        ax_info.text(0.5, 0.97, 'Link Inspector',
                     transform=ax_info.transAxes, ha='center', va='top',
                     fontsize=13, fontweight='bold', color='#1a202c')

        if lid is None:
            ax_info.text(0.5, 0.84, 'Click any link\nto inspect it.',
                         transform=ax_info.transAxes, ha='center', va='top',
                         fontsize=11, color='#6b7280',
                         bbox=dict(boxstyle='round', fc='white', alpha=0.8))
            return

        u, v, k   = idx_to_edge[lid]
        edata     = G[u][v][k]
        ltype     = edata.get('link_type', 'mixed')
        x_val     = float(x_all[lid, frame])
        d_val     = float(link_demand[lid, frame])
        f_val     = outflow_fn(x_val)
        lat_val   = latency_fn(x_val)

        y_c = 0.90
        ax_info.text(0.5, y_c, f'{u}  →  {v}',
                     transform=ax_info.transAxes, ha='center', va='top',
                     fontsize=12, fontweight='bold', color='#1a202c')
        y_c -= 0.055
        ax_info.text(0.5, y_c, f'Link {lid}  |  {ltype}',
                     transform=ax_info.transAxes, ha='center', va='top',
                     fontsize=9, color='#6b7280')
        y_c -= 0.065

        ax_info.plot([0.02, 0.98], [y_c + 0.01, y_c + 0.01],
                     transform=ax_info.transAxes, color='#e2e8f0', lw=1.2, clip_on=False)

        def row(y, lbl, val, vc='#1d4ed8'):
            ax_info.text(0.05, y, lbl, transform=ax_info.transAxes,
                         va='top', fontsize=10, color='#374151')
            ax_info.text(0.95, y, val, transform=ax_info.transAxes,
                         va='top', ha='right', fontsize=10,
                         color=vc, fontweight='bold')

        for lbl, val, vc in [
            ('Density  x_i',  f'{x_val:.4f}',   '#1d4ed8'),
            ('Demand  y_i',   f'{d_val:.4f}',   '#1d4ed8'),
            ('Outflow  f_i',  f'{f_val:.4f}',   '#0369a1'),
            ('Latency  l_i',  f'{lat_val:.4f}', '#0369a1'),
        ]:
            row(y_c, lbl, val, vc); y_c -= 0.075

        if ltype == 'EV-only':
            sid    = edata.get('station_id', '?')
            sp     = get_station_parameters(t_now, sid)
            svc    = outflow_fn(x_val, mu=sp['mu_s'], nu=sp['nu_s'], is_charging=True)
            wt     = x_val / max(sp['mu_s'], 1e-9)
            profit = (sp['p_s'] - sp['c_s']) * svc

            y_c -= 0.02
            ax_info.plot([0.02, 0.98], [y_c + 0.01, y_c + 0.01],
                         transform=ax_info.transAxes, color='#bbf7d0', lw=1.5, clip_on=False)
            ax_info.text(0.5, y_c, f'Station {sid}',
                         transform=ax_info.transAxes, ha='center', va='top',
                         fontsize=11, fontweight='bold', color='#166534')
            y_c -= 0.075

            for lbl, val, vc in [
                ('Price  p_s',      f'${sp["p_s"]:.2f}/veh',   '#15803d'),
                ('Service rate mu', f'{sp["mu_s"]:.2f} veh/s', '#15803d'),
                ('Op. cost  c_s',   f'${sp["c_s"]:.2f}/veh',   '#166534'),
                ('Queue length',    f'{x_val:.4f}',             '#b45309'),
                ('Wait time  w_s',  f'{wt:.4f} s',              '#b45309'),
                ('Svc rate  f_is',  f'{svc:.4f} veh/s',         '#166534'),
                ('Profit rate  Pi', f'${profit:.4f}/s',
                 '#15803d' if profit >= 0 else '#dc2626'),
            ]:
                row(y_c, lbl, val, vc); y_c -= 0.075

    # ---------- ANIMATION ----------
    frame_step = max(1, n_t // 250)

    def start_anim(event=None):
        if anim_obj[0] is not None:
            try: anim_obj[0].event_source.stop()
            except: pass
        def _animate(fi):
            state['frame'] = fi
            draw_frame(fi)
        frames = list(range(state['frame'], n_t, frame_step))
        anim_obj[0] = animation.FuncAnimation(
            fig, _animate, frames=frames, interval=80, repeat=False)
        fig.canvas.draw_idle()

    # Buttons
    ax_play = fig.add_axes([0.02, 0.025, 0.09, 0.055])
    ax_stop = fig.add_axes([0.13, 0.025, 0.09, 0.055])
    ax_rew  = fig.add_axes([0.24, 0.025, 0.09, 0.055])
    btn_play = Button(ax_play, 'Play',  color='#dcfce7', hovercolor='#bbf7d0')
    btn_stop = Button(ax_stop, 'Pause', color='#fee2e2', hovercolor='#fecaca')
    btn_rew  = Button(ax_rew,  'Reset', color='#dbeafe', hovercolor='#bfdbfe')

    def on_stop(e):
        if anim_obj[0]:
            try: anim_obj[0].event_source.stop()
            except: pass
    def on_rew(e):
        on_stop(e)
        state['frame'] = 0
        draw_frame(0)

    btn_play.on_clicked(start_anim)
    btn_stop.on_clicked(on_stop)
    btn_rew.on_clicked(on_rew)

    # ---------- INTERACTION ----------
    def arc_pts(x1, y1, x2, y2, rad, n=14):
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        dx, dy = x2 - x1, y2 - y1
        nm    = max(np.hypot(dx, dy), 1e-9)
        px, py = -dy / nm, dx / nm
        offset = rad * nm * 0.5
        cx, cy = mx + px * offset, my + py * offset
        pts = []
        for tt in np.linspace(0, 1, n):
            bx = (1 - tt) ** 2 * x1 + 2 * (1 - tt) * tt * cx + tt ** 2 * x2
            by = (1 - tt) ** 2 * y1 + 2 * (1 - tt) * tt * cy + tt ** 2 * y2
            pts.append((bx, by))
        return pts

    def find_nearest_link(mx, my, thresh=0.55):
        best_lid, best_d = None, thresh
        for u, v, k, edata in edges_list:
            if u == v: continue
            lt = edata.get('link_type', 'mixed')
            if lt in ('origin', 'destination'): continue
            par  = parallel_map.get((u, v), [])
            n_p  = len(par)
            ip   = par.index(k) if k in par else 0
            rad  = (+0.28 if ip == 0 else -0.28) if n_p > 1 else 0.0
            x1, y1 = pos[u]; x2, y2 = pos[v]
            d = min(np.hypot(mx - ppx, my - ppy)
                    for ppx, ppy in arc_pts(x1, y1, x2, y2, rad))
            if d < best_d:
                best_d, best_lid = d, edata['link_id']
        return best_lid

    drag = {'node': None}

    def on_press(event):
        if event.inaxes != ax_net or event.xdata is None: return
        mx, my = event.xdata, event.ydata
        for node, (nx_, ny_) in pos.items():
            if np.hypot(mx - nx_, my - ny_) < 0.5:
                drag['node'] = node
                return
        lid = find_nearest_link(mx, my)
        if lid is not None:
            state['selected_link'] = (None if state['selected_link'] == lid else lid)
            draw_frame(state['frame'])

    def on_release(event):
        drag['node'] = None

    def on_motion(event):
        if drag['node'] is None or event.inaxes != ax_net: return
        if event.xdata is None: return
        pos[drag['node']] = [event.xdata, event.ydata]
        draw_frame(state['frame'])

    fig.canvas.mpl_connect('button_press_event',   on_press)
    fig.canvas.mpl_connect('button_release_event', on_release)
    fig.canvas.mpl_connect('motion_notify_event',  on_motion)

    draw_frame(0)
    plt.show()


# ══════════════════════════════════════════════════════
#  SHARED HELPER
# ══════════════════════════════════════════════════════
def od_label(od, idx_to_edge, G):
    u0, v0, k0 = idx_to_edge[od[0]]
    u1, v1, k1 = idx_to_edge[od[1]]
    on = G[u0][v0][k0].get('origin_id', u0)
    dn = G[u1][v1][k1].get('dest_id',   u1)
    return on, dn


# ══════════════════════════════════════════════════════
#  FIGURE 2 – PATH DEMAND DYNAMICS
# ══════════════════════════════════════════════════════
def plot_path_demands(t, y_EV_all, y_NEV_all,
                      paths_EV, paths_NEV,
                      od_pairs_EV, od_pairs_NEV,
                      lambda_EV, lambda_NEV, G, idx_to_edge):
    plots = []

    idx = 0
    for od in od_pairs_NEV:
        np_od = len(paths_NEV[od])
        on, dn = od_label(od, idx_to_edge, G)
        plots.append(dict(title=f'NEV: {on} -> {dn}',
                          data=y_NEV_all[idx:idx + np_od, :],
                          demand=lambda_NEV[od]))
        idx += np_od

    idx = 0
    for od in od_pairs_EV:
        np_od = len(paths_EV[od])
        on, dn = od_label(od, idx_to_edge, G)
        plots.append(dict(title=f'EV: {on} -> {dn}',
                          data=y_EV_all[idx:idx + np_od, :],
                          demand=lambda_EV[od]))
        idx += np_od

    if not plots:
        print("  No path-demand data to plot."); return

    n_cols = 2
    n_rows = (len(plots) + 1) // 2
    fig, axs = plt.subplots(n_rows, n_cols, figsize=(16, 5 * n_rows))
    fig.suptitle('Path Demand Dynamics', fontsize=16, fontweight='bold')
    plt.subplots_adjust(hspace=0.45, wspace=0.30, top=0.93)
    axs = axs.flatten() if len(plots) > 1 else [axs]

    for i, info in enumerate(plots):
        ax = axs[i]
        for pi in range(info['data'].shape[0]):
            ax.plot(t, info['data'][pi, :], lw=2, label=f'Path {pi}')
        ax.axhline(info['demand'], color='red', ls='--', lw=2,
                   label=f"Total Demand={info['demand']:.2f}")
        ax.set_title(info['title'], fontsize=12, fontweight='bold')
        ax.set_xlabel('Time'); ax.set_ylabel('Path Flow')
        ax.grid(True, alpha=0.3); ax.legend(fontsize=8)

    for i in range(len(plots), len(axs)):
        axs[i].axis('off')
    plt.show()


# ══════════════════════════════════════════════════════
#  FIGURE 3 – REPLICATOR CONVERGENCE
# ══════════════════════════════════════════════════════
def plot_cost_convergence(t_all, x_all, y_EV_all, y_NEV_all,
                          paths_EV, paths_NEV,
                          od_pairs_EV, od_pairs_NEV,
                          lambda_EV, lambda_NEV, idx_to_edge, G):
    step   = max(1, len(t_all) // 400)
    t_sub  = t_all[::step]
    x_sub  = x_all[:, ::step]
    yEVs   = y_EV_all[:, ::step]
    yNEVs  = y_NEV_all[:, ::step]
    n_sub  = len(t_sub)

    def gap_series(od_pairs, paths_dict, y_sub, lam_dict, vcls):
        results = []
        pidx = 0
        for od in od_pairs:
            paths = paths_dict[od]
            np_od = len(paths)
            lam   = lam_dict[od]
            gaps  = np.zeros((np_od, n_sub))
            for ti in range(n_sub):
                x_t  = x_sub[:, ti]
                y_od = np.maximum(y_sub[pidx:pidx + np_od, ti], 0.0)
                tot  = y_od.sum()
                y_n  = y_od * (lam / tot) if tot > 1e-12 else np.full(np_od, lam / np_od)
                tau_p = []
                for path in paths:
                    c = 0.0
                    for lid in path:
                        u, v, k = idx_to_edge[lid]
                        d  = G[u][v][k]
                        lt = d.get('link_type', 'mixed')
                        if lt in ('origin', 'destination'): continue
                        elif lt == 'EV-only' and vcls == 'EV':
                            sid = d['station_id']
                            sp  = get_station_parameters(t_sub[ti], sid)
                            xi  = x_t[lid]
                            wt  = xi / max(sp['mu_s'], 1e-9)
                            c  += latency_fn(xi, True) + alpha * wt + gamma * sp['p_s']
                        else:
                            c += latency_fn(x_t[lid])
                    tau_p.append(c)
                tau_p  = np.array(tau_p)
                tau_avg = (y_n * tau_p).sum() / max(lam, 1e-12)
                gaps[:, ti] = tau_avg - tau_p
            on, dn = od_label(od, idx_to_edge, G)
            results.append(dict(title=f'{vcls}: {on}->{dn}', gaps=gaps))
            pidx += np_od
        return results

    all_res = (gap_series(od_pairs_NEV, paths_NEV, yNEVs, lambda_NEV, 'NEV') +
               gap_series(od_pairs_EV,  paths_EV,  yEVs,  lambda_EV,  'EV'))

    if not all_res: return

    n_cols = 2
    n_rows = (len(all_res) + 1) // 2
    fig, axs = plt.subplots(n_rows, n_cols, figsize=(16, 5 * n_rows))
    fig.suptitle('Replicator Convergence:  tau_avg - tau_p  ->  0',
                 fontsize=16, fontweight='bold')
    plt.subplots_adjust(hspace=0.45, wspace=0.30, top=0.93)
    axs = axs.flatten() if len(all_res) > 1 else [axs]

    for i, res in enumerate(all_res):
        ax = axs[i]
        for pi in range(res['gaps'].shape[0]):
            ax.plot(t_sub, res['gaps'][pi, :], lw=2, label=f'Path {pi}')
        ax.axhline(0, color='red', ls='--', lw=1.5, label='Equilibrium (0)')
        ax.set_title(res['title'], fontsize=12, fontweight='bold')
        ax.set_xlabel('Time'); ax.set_ylabel('tau_avg - tau_p')
        ax.grid(True, alpha=0.3); ax.legend(fontsize=8)

    for i in range(len(all_res), len(axs)):
        axs[i].axis('off')
    plt.show()


# ══════════════════════════════════════════════════════
#  FIGURE 4 – COMPETITION METRICS
# ══════════════════════════════════════════════════════
def plot_charging_station_metrics(q_s_traj, p_s_traj, t, charging_stations, x_traj):
    station_ids = sorted(charging_stations.keys())
    colors = {'S1': '#e74c3c', 'S2': '#3498db'}

    fig, axs = plt.subplots(2, 3, figsize=(20, 11))
    fig.suptitle('Competition Metrics (Dynamic Pricing Game)',
                 fontsize=18, fontweight='bold', color='#2c3e50')
    fig.patch.set_facecolor('#ecf0f1')

    phases = [
        ('Phase 1\n(0-100s)',   0,   100),
        ('Phase 2\n(100-200s)', 100, 200),
        ('Phase 3\n(200-300s)', 200, 300),
        ('Phase 4\n(300-400s)', 300, 400),
    ]
    x_pos = np.arange(len(phases)); width = 0.30

    # 1 Market Share
    ax = axs[0, 0]
    tot = sum(q_s_traj[s] for s in station_ids) + 1e-9
    for sid in station_ids:
        ms = 100 * q_s_traj[sid] / tot
        ax.plot(t, ms, label=sid, lw=3, color=colors[sid], alpha=0.9)
        ax.fill_between(t, 0, ms, color=colors[sid], alpha=0.12)
    for pt in [100, 200, 300]:
        ax.axvline(pt, color='gray', ls='--', alpha=0.4, lw=1.5)
    ax.set_title('Market Share Evolution', fontweight='bold', fontsize=13)
    ax.set_ylabel('Market Share (%)'); ax.set_xlabel('Time (s)')
    ax.set_ylim(0, 105); ax.grid(True, alpha=0.2, ls='--')
    ax.legend(fontsize=10, framealpha=0.95); ax.set_facecolor('#fafafa')

    # 2 Pricing
    ax = axs[0, 1]
    for sid in station_ids:
        ax.plot(t, p_s_traj[sid], label=sid, lw=3, color=colors[sid],
                marker='o', markevery=100, ms=4, alpha=0.9)
    for pt in [100, 200, 300]:
        ax.axvline(pt, color='gray', ls='--', alpha=0.4, lw=1.5)
    ax.set_title('Pricing Strategy', fontweight='bold', fontsize=13)
    ax.set_ylabel('Price ($/vehicle)'); ax.set_xlabel('Time (s)')
    ax.grid(True, alpha=0.2, ls='--')
    ax.legend(fontsize=10, framealpha=0.95); ax.set_facecolor('#fafafa')

    # 3 Queues
    ax = axs[0, 2]
    for sid in station_ids:
        lid = charging_stations[sid]
        ax.plot(t, x_traj[lid, :], label=sid, lw=3, color=colors[sid], alpha=0.9)
    for pt in [100, 200, 300]:
        ax.axvline(pt, color='gray', ls='--', alpha=0.4, lw=1.5)
    ax.set_title('Queue Lengths', fontweight='bold', fontsize=13)
    ax.set_ylabel('Vehicles in Queue'); ax.set_xlabel('Time (s)')
    ax.grid(True, alpha=0.2, ls='--')
    ax.legend(fontsize=10, framealpha=0.95); ax.set_facecolor('#fafafa')

    # 4 Revenue
    ax = axs[1, 0]
    for i, sid in enumerate(station_ids):
        revs = []
        for _, ts, te in phases:
            mask = (t >= ts) & (t <= te); tp = t[mask]
            revs.append(np.trapezoid(p_s_traj[sid][mask] * q_s_traj[sid][mask], tp)
                        if len(tp) > 1 else 0.0)
        bars = ax.bar(x_pos + i * width, revs, width, label=sid,
                      color=colors[sid], alpha=0.85, edgecolor='white', lw=2)
        for xp, rv in zip(x_pos + i * width, revs):
            if rv > 0.05:
                ax.text(xp, rv + 0.04, f'{rv:.2f}', ha='center', va='bottom',
                        fontsize=8, fontweight='bold')
    ax.set_xticks(x_pos + width * 0.5)
    ax.set_xticklabels([p[0] for p in phases], fontsize=9)
    ax.set_ylabel('Integrated Revenue ($*veh)')
    ax.set_title('Revenue by Phase', fontweight='bold', fontsize=13)
    ax.legend(fontsize=10, framealpha=0.95); ax.grid(True, alpha=0.2, axis='y', ls='--')
    ax.set_facecolor('#fafafa')

    # 5 Net Profit
    ax = axs[1, 1]
    for i, sid in enumerate(station_ids):
        profits = []
        for _, ts, te in phases:
            mask = (t >= ts) & (t <= te); tp = t[mask]
            if len(tp) > 1:
                cs = np.array([get_station_parameters(ti, sid)['c_s'] for ti in tp])
                profits.append(
                    np.trapezoid((p_s_traj[sid][mask] - cs) * q_s_traj[sid][mask], tp))
            else:
                profits.append(0.0)
        bars = ax.bar(x_pos + i * width, profits, width, label=sid,
                      color=colors[sid], alpha=0.85, edgecolor='white', lw=2)
        for xp, pf in zip(x_pos + i * width, profits):
            if abs(pf) > 0.05:
                ax.text(xp, pf + (0.04 if pf >= 0 else -0.04), f'{pf:.2f}',
                        ha='center', va='bottom' if pf >= 0 else 'top',
                        fontsize=8, fontweight='bold')
    ax.set_xticks(x_pos + width * 0.5)
    ax.set_xticklabels([p[0] for p in phases], fontsize=9)
    ax.set_ylabel('Integrated Net Profit ($*veh)')
    ax.set_title('Net Profit by Phase', fontweight='bold', fontsize=13)
    ax.legend(fontsize=10, framealpha=0.95); ax.grid(True, alpha=0.2, axis='y', ls='--')
    ax.axhline(0, color='black', ls='-', alpha=0.3, lw=1.5); ax.set_facecolor('#fafafa')

    # 6 Overall Market Share
    ax = axs[1, 2]
    tot_int = {sid: np.trapezoid(q_s_traj[sid], t) for sid in station_ids}
    grand   = sum(tot_int.values()) + 1e-9
    shares  = [100 * tot_int[s] / grand for s in station_ids]
    bars = ax.bar(range(len(station_ids)), shares,
                  color=[colors[s] for s in station_ids],
                  edgecolor='white', lw=3, alpha=0.85)
    ax.set_xticks(range(len(station_ids)))
    ax.set_xticklabels(station_ids, fontsize=12, fontweight='bold')
    ax.set_ylabel('Market Share (%)')
    ax.set_title('Overall Market Share', fontweight='bold', fontsize=13)
    ax.set_ylim(0, 110); ax.grid(True, alpha=0.2, axis='y', ls='--')
    ax.set_facecolor('#fafafa')
    for bar, pct, sid in zip(bars, shares, station_ids):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2,
                f'{pct:.1f}%', ha='center', va='bottom',
                fontweight='bold', fontsize=12, color=colors[sid])

    plt.tight_layout(rect=[0, 0.02, 1, 0.97])
    plt.show()


# ──────────────────────────────────────────────────────
if __name__ == '__main__':
    run_simulation()
    print("\n" + "=" * 70)
    print("SIMULATION COMPLETE")
    print("=" * 70)