"""
EV Charging Station Competition Simulation - TC9 (9-node, 4-station network)
Web-compatible version for server deployment
"""
import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.animation as animation
from scipy.integrate import solve_ivp
import warnings
warnings.filterwarnings('ignore')

# --- REPLICATOR DYNAMICS PARAMETERS ---
eta_EV = 0.05
eta_NEV = 0.05
alpha = 0.3
gamma = 1.0
k_rep = 10.0

# --- TRAFFIC FLOW PARAMETERS ---
LINK_CAP = 1.5
LINK_STEEP = 1.0

# --- SIMULATION PARAMETERS (defaults, can be overridden) ---
T_FINAL = 200.0  # Reduced for web
N_TIME_POINTS = 400
SOLVER_RTOL = 1e-4
SOLVER_ATOL = 1e-6
MAX_STEP = 5.0


# ──────────────────────────────────────────────────────
#  PIECEWISE PRICING
# ──────────────────────────────────────────────────────
def get_station_parameters(t, station_id, t_final=500.0):
    """Get station parameters with scaled phase boundaries"""
    # Scale phase boundaries to simulation duration
    scale = t_final / 500.0
    p1, p2, p3 = 125 * scale, 250 * scale, 375 * scale
    
    if station_id == 'S1':
        if   t < p1: return {'p_s': 0.55, 'mu_s': 1.2, 'c_s': 0.10, 'nu_s':  8.0}
        elif t < p2: return {'p_s': 0.15, 'mu_s': 1.5, 'c_s': 0.10, 'nu_s': 10.0}
        elif t < p3: return {'p_s': 0.65, 'mu_s': 2.0, 'c_s': 0.15, 'nu_s': 12.0}
        else:        return {'p_s': 0.45, 'mu_s': 2.5, 'c_s': 0.15, 'nu_s': 15.0}
    elif station_id == 'S2':
        if   t < p1: return {'p_s': 0.55, 'mu_s': 1.2, 'c_s': 0.10, 'nu_s':  8.0}
        elif t < p2: return {'p_s': 0.70, 'mu_s': 1.2, 'c_s': 0.10, 'nu_s':  8.0}
        elif t < p3: return {'p_s': 0.15, 'mu_s': 1.5, 'c_s': 0.12, 'nu_s': 10.0}
        else:        return {'p_s': 0.45, 'mu_s': 2.0, 'c_s': 0.15, 'nu_s': 13.0}
    elif station_id == 'S3':
        if   t < p1: return {'p_s': 0.25, 'mu_s': 1.8, 'c_s': 0.10, 'nu_s': 10.0}
        elif t < p2: return {'p_s': 0.35, 'mu_s': 1.8, 'c_s': 0.10, 'nu_s': 10.0}
        elif t < p3: return {'p_s': 0.60, 'mu_s': 2.2, 'c_s': 0.14, 'nu_s': 13.0}
        else:        return {'p_s': 0.40, 'mu_s': 2.5, 'c_s': 0.14, 'nu_s': 15.0}
    elif station_id == 'S4':
        if   t < p1: return {'p_s': 0.20, 'mu_s': 1.8, 'c_s': 0.10, 'nu_s': 10.0}
        elif t < p2: return {'p_s': 0.30, 'mu_s': 1.8, 'c_s': 0.10, 'nu_s': 10.0}
        elif t < p3: return {'p_s': 0.45, 'mu_s': 2.2, 'c_s': 0.12, 'nu_s': 13.0}
        else:        return {'p_s': 0.38, 'mu_s': 2.5, 'c_s': 0.14, 'nu_s': 15.0}
    return {'p_s': 0.5, 'mu_s': 1.5, 'c_s': 0.1, 'nu_s': 10.0}


# ──────────────────────────────────────────────────────
#  NETWORK CONSTRUCTION
# ──────────────────────────────────────────────────────
def create_network():
    """
    Network topology (9-node, 4-station):
    - O1 -> V2 -> D1 (via S1) or O1 -> V1 -> D1 (via S2)
    - O2 -> V3 -> D2/D3 (via S3) or O2 -> V4 -> D3 (via S4)
    """
    G = nx.MultiDiGraph()

    for n in ['O1','O2','V1','V2','V3','V4','D1','D2','D3']:
        G.add_node(n)

    # Origin self-loops
    G.add_edge('O1','O1', key=0, link_type='origin', origin_id='O1', is_origin=True)
    G.add_edge('O2','O2', key=0, link_type='origin', origin_id='O2', is_origin=True)

    # O1 roads
    G.add_edge('O1','V2', key=0, link_type='mixed')
    G.add_edge('O1','V1', key=0, link_type='mixed')

    # V2 roads (S1 branch)
    G.add_edge('V2','D1', key=0, link_type='mixed')
    G.add_edge('V2','D1', key=1, link_type='EV-only', station_id='S1')

    # V1 roads (S2 branch)
    G.add_edge('V1','D1', key=0, link_type='mixed')
    G.add_edge('V1','D1', key=1, link_type='EV-only', station_id='S2')

    # O2 roads
    G.add_edge('O2','V4', key=0, link_type='mixed')
    G.add_edge('O2','V3', key=0, link_type='mixed')
    G.add_edge('O2','V3', key=1, link_type='EV-only', station_id='S3')

    # V4 roads
    G.add_edge('V4','D3', key=0, link_type='mixed')
    G.add_edge('V4','D3', key=1, link_type='EV-only', station_id='S4')

    # V3 roads
    G.add_edge('V3','V4', key=0, link_type='mixed')
    G.add_edge('V3','V1', key=0, link_type='mixed')
    G.add_edge('V3','D2', key=0, link_type='mixed')
    G.add_edge('V3','D3', key=0, link_type='mixed')

    # Destination self-loops
    G.add_edge('D1','D1', key=0, link_type='destination', dest_id='D1', is_destination=True)
    G.add_edge('D2','D2', key=0, link_type='destination', dest_id='D2', is_destination=True)
    G.add_edge('D3','D3', key=0, link_type='destination', dest_id='D3', is_destination=True)

    # Assign link_id
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
        'O1': (0, 8), 'V2': (5, 10), 'V1': (5, 6), 'D1': (10, 8),
        'O2': (0, 2), 'V3': (7, 4), 'V4': (3, 0), 'D2': (11, 4), 'D3': (7, 0),
    }
    nx.set_node_attributes(G, pos, 'pos')

    return G, origins, destinations, charging_stations, idx_to_edge, edge_to_idx


# ──────────────────────────────────────────────────────
#  PATH ENUMERATION
# ──────────────────────────────────────────────────────
def enumerate_paths(G, origins, destinations, charging_stations, idx_to_edge, edge_to_idx):
    paths_EV = {}
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
                                + [edge_to_idx[(u,v,k)] for u,v,k in path_edges]
                                + [d_idx])

                    ev_cnt = sum(1 for lid in path_ids
                                 if G[idx_to_edge[lid][0]][idx_to_edge[lid][1]]
                                     [idx_to_edge[lid][2]].get('link_type') == 'EV-only')

                    if ev_cnt == 0:
                        mixed.append(path_ids)
                    elif ev_cnt == 1:
                        charging.append(path_ids)

            paths_NEV[od] = mixed
            paths_EV[od] = mixed + charging if charging else mixed

    return paths_EV, paths_NEV


# ──────────────────────────────────────────────────────
#  OD DEMAND
# ──────────────────────────────────────────────────────
def create_od_demand(G, origins, destinations, idx_to_edge):
    origin_name_to_idx = {}
    dest_name_to_idx = {}
    for i, (u, v, k) in enumerate(idx_to_edge):
        d = G[u][v][k]
        if d.get('is_origin'):
            origin_name_to_idx[d['origin_id']] = i
        if d.get('is_destination'):
            dest_name_to_idx[d['dest_id']] = i

    scenario = {
        'O1': {'total_flow': 1.0, 'beta_EV': 0.6, 'destinations': {'D1': 1.0}},
        'O2': {'total_flow': 1.2, 'beta_EV': 0.5, 'destinations': {'D2': 0.5, 'D3': 0.5}},
    }

    lambda_EV, lambda_NEV = {}, {}
    for oname, cfg in scenario.items():
        o_idx = origin_name_to_idx[oname]
        for dname, frac in cfg['destinations'].items():
            d_idx = dest_name_to_idx[dname]
            od = (o_idx, d_idx)
            lambda_EV[od] = cfg['total_flow'] * cfg['beta_EV'] * frac
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
#  ROUTING MATRIX
# ──────────────────────────────────────────────────────
def compute_routing_matrix(y_EV, y_NEV, paths_EV, paths_NEV, od_pairs_EV, od_pairs_NEV, n_links):
    pair_demand = {}

    def accumulate(od_pairs, paths_dict, y_vec):
        p_idx = 0
        for od in od_pairs:
            for path in paths_dict[od]:
                yp = float(y_vec[p_idx])
                for step in range(len(path) - 1):
                    j, i = path[step], path[step+1]
                    pair_demand[(j,i)] = pair_demand.get((j,i), 0.0) + yp
                p_idx += 1

    accumulate(od_pairs_EV, paths_EV, y_EV)
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
            succs = [ii for (jj,ii) in pair_demand if jj == j]
            R[j, i] = 1.0 / max(len(succs), 1)

    return R


# ──────────────────────────────────────────────────────
#  PATH COSTS
# ──────────────────────────────────────────────────────
def compute_path_costs(x, paths_dict, od_pairs, idx_to_edge, G, t, t_final, vcls='EV'):
    costs = []
    for od in od_pairs:
        for path in paths_dict[od]:
            cost = 0.0
            for lid in path:
                u, v, k = idx_to_edge[lid]
                d = G[u][v][k]
                lt = d.get('link_type', 'mixed')
                if lt in ('origin', 'destination'):
                    continue
                elif lt == 'EV-only' and vcls == 'EV':
                    sid = d['station_id']
                    sp = get_station_parameters(t, sid, t_final)
                    xi = x[lid]
                    wt = xi / max(sp['mu_s'], 1e-9)
                    cost += latency_fn(xi, True) + alpha * wt + gamma * sp['p_s']
                else:
                    cost += latency_fn(x[lid])
            costs.append(cost)
    return np.array(costs)


# ──────────────────────────────────────────────────────
#  COUPLED ODE
# ──────────────────────────────────────────────────────
def coupled_dynamics(t, state, params):
    n_links = params['n_links']
    n_pEV = params['n_paths_EV']
    G = params['G']
    idx_to_edge = params['idx_to_edge']
    t_final = params['t_final']

    x = state[:n_links]
    y_EV = state[n_links:n_links + n_pEV]
    y_NEV = state[n_links + n_pEV:]

    # outflows
    f = np.zeros(n_links)
    for i in range(n_links):
        u, v, k = idx_to_edge[i]
        d = G[u][v][k]
        lt = d.get('link_type', 'mixed')
        if lt == 'origin':
            f[i] = params['lambda_origin'][i]
        elif lt == 'EV-only':
            sp = get_station_parameters(t, d['station_id'], t_final)
            f[i] = outflow_fn(x[i], mu=sp['mu_s'], nu=sp['nu_s'], is_charging=True)
        else:
            f[i] = outflow_fn(x[i])

    # routing matrix
    R = compute_routing_matrix(y_EV, y_NEV,
                               params['paths_EV'], params['paths_NEV'],
                               params['od_pairs_EV'], params['od_pairs_NEV'],
                               n_links)

    dx_dt = R.T @ f - f

    # replicator - EV
    tau_EV = compute_path_costs(x, params['paths_EV'], params['od_pairs_EV'],
                                idx_to_edge, G, t, t_final, 'EV')
    dy_EV_dt = np.zeros(n_pEV)
    idx = 0
    for od in params['od_pairs_EV']:
        np_od = len(params['paths_EV'][od])
        lam = params['lambda_od_EV'][od]
        y_od = np.maximum(y_EV[idx:idx+np_od], 1e-9)
        total = y_od.sum()
        y_od = y_od*(lam/total) if total > 1e-12 else np.full(np_od, lam/np_od)
        if lam > 1e-9:
            tau_od = tau_EV[idx:idx+np_od]
            tau_avg = (y_od * tau_od).sum() / lam
            for ii in range(np_od):
                dy_EV_dt[idx+ii] = k_rep * eta_EV * y_od[ii] * (tau_avg - tau_od[ii])
        idx += np_od

    # replicator - NEV
    tau_NEV = compute_path_costs(x, params['paths_NEV'], params['od_pairs_NEV'],
                                 idx_to_edge, G, t, t_final, 'NEV')
    n_pNEV = params['n_paths_NEV']
    dy_NEV_dt = np.zeros(n_pNEV)
    idx = 0
    for od in params['od_pairs_NEV']:
        np_od = len(params['paths_NEV'][od])
        lam = params['lambda_od_NEV'][od]
        y_od = np.maximum(y_NEV[idx:idx+np_od], 1e-9)
        total = y_od.sum()
        y_od = y_od*(lam/total) if total > 1e-12 else np.full(np_od, lam/np_od)
        if lam > 1e-9:
            tau_od = tau_NEV[idx:idx+np_od]
            tau_avg = (y_od * tau_od).sum() / lam
            for ii in range(np_od):
                dy_NEV_dt[idx+ii] = k_rep * eta_NEV * y_od[ii] * (tau_avg - tau_od[ii])
        idx += np_od

    return np.concatenate([dx_dt, dy_EV_dt, dy_NEV_dt])


# ──────────────────────────────────────────────────────
#  MAIN SIMULATION RUNNER
# ──────────────────────────────────────────────────────
def run_simulation(save_animation_path=None, t_final=None, n_points=None, return_data=False):
    """Main simulation runner for web deployment
    
    Args:
        save_animation_path: Path to save animation GIF
        t_final: Simulation duration (default: T_FINAL)
        n_points: Number of time points (default: N_TIME_POINTS)
        return_data: If True, returns network data for interactive visualization
    """
    sim_t_final = t_final if t_final is not None else T_FINAL
    sim_n_points = n_points if n_points is not None else N_TIME_POINTS

    print("\n" + "="*70)
    print("EV CHARGING STATION COMPETITION - TC9 (9-node, 4-station)")
    print("="*70)

    (G, origins, destinations, charging_stations,
     idx_to_edge, edge_to_idx) = create_network()

    paths_EV, paths_NEV = enumerate_paths(
        G, origins, destinations, charging_stations, idx_to_edge, edge_to_idx)
    lambda_EV, lambda_NEV = create_od_demand(
        G, origins, destinations, idx_to_edge)

    n_links = len(idx_to_edge)
    print(f"Network: {n_links} links, {len(charging_stations)} stations")

    # Build active OD pair lists
    od_pairs_EV, y_EV_0 = [], []
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

    x0 = np.zeros(n_links)
    state0 = np.concatenate([x0, y_EV_0, y_NEV_0])
    n_paths_EV = len(y_EV_0)
    n_paths_NEV = len(y_NEV_0)

    print(f"State dim: {len(state0)} = {n_links} links + {n_paths_EV} EV paths + {n_paths_NEV} NEV paths")
    print(f"Duration: {sim_t_final}s, Time points: {sim_n_points}")

    # origin constant outflows
    lambda_origin = np.zeros(n_links)
    for o_idx in origins:
        lam = (sum(lambda_EV.get((o_idx,d), 0.0) for d in destinations) +
               sum(lambda_NEV.get((o_idx,d), 0.0) for d in destinations))
        lambda_origin[o_idx] = lam

    params = dict(
        n_links=n_links, n_paths_EV=n_paths_EV, n_paths_NEV=n_paths_NEV,
        paths_EV=paths_EV, paths_NEV=paths_NEV,
        od_pairs_EV=od_pairs_EV, od_pairs_NEV=od_pairs_NEV,
        lambda_od_EV=lambda_EV, lambda_od_NEV=lambda_NEV,
        lambda_origin=lambda_origin,
        charging_stations=charging_stations,
        G=G, idx_to_edge=idx_to_edge,
        t_final=sim_t_final,
    )

    # Single-phase integration (simpler for web)
    print("Running simulation...")
    t_eval = np.linspace(0, sim_t_final, sim_n_points)
    
    sol = solve_ivp(lambda t, s: coupled_dynamics(t, s, params),
                    [0, sim_t_final], state0,
                    method='Radau', t_eval=t_eval,
                    rtol=SOLVER_RTOL, atol=SOLVER_ATOL, max_step=MAX_STEP)
    
    print(f"Simulation {'OK' if sol.success else 'WARN'}: {len(sol.t)} pts")

    sol.y[:n_links, :] = np.maximum(sol.y[:n_links, :], 0.0)

    t_all = sol.t
    x_all = sol.y[:n_links, :]
    y_EV_all = sol.y[n_links:n_links+n_paths_EV, :]
    y_NEV_all = sol.y[n_links+n_paths_EV:, :]

    # Station metrics
    q_s, p_s = {}, {}
    for sid, lid in charging_stations.items():
        q_s[sid] = np.array([
            outflow_fn(x_all[lid, i],
                       mu=get_station_parameters(t_all[i], sid, sim_t_final)['mu_s'],
                       nu=get_station_parameters(t_all[i], sid, sim_t_final)['nu_s'],
                       is_charging=True)
            for i in range(len(t_all))])
        p_s[sid] = np.array([
            get_station_parameters(t_all[i], sid, sim_t_final)['p_s']
            for i in range(len(t_all))])

    # Create visualizations
    print("Creating visualizations...")
    
    print("   [VIZ 1/4] Network animation...")
    create_network_animation(G, x_all, t_all, idx_to_edge, charging_stations,
                            sim_t_final, save_path=save_animation_path,
                            n_frames=min(50, sim_n_points // 4))
    
    print("   [VIZ 2/4] Path demands...")
    plot_path_demands(t_all, y_EV_all, y_NEV_all, paths_EV, paths_NEV,
                     od_pairs_EV, od_pairs_NEV, lambda_EV, lambda_NEV,
                     G, idx_to_edge)
    
    print("   [VIZ 3/4] Replicator convergence...")
    plot_cost_convergence(t_all, x_all, y_EV_all, y_NEV_all,
                         paths_EV, paths_NEV, od_pairs_EV, od_pairs_NEV,
                         lambda_EV, lambda_NEV, idx_to_edge, G, sim_t_final)
    
    print("   [VIZ 4/4] Competition metrics...")
    plot_charging_station_metrics(q_s, p_s, t_all, charging_stations, x_all, sim_t_final)
    
    # Return network data for interactive visualization
    if return_data:
        pos = nx.get_node_attributes(G, 'pos')
        # Build nodes list
        nodes = []
        for node in G.nodes():
            x_pos, y_pos = pos.get(node, (0, 0))
            if node.startswith('O'):
                node_type = 'origin'
            elif node.startswith('D'):
                node_type = 'destination'
            else:
                node_type = 'intermediate'
            nodes.append({
                'id': node,
                'x': float(x_pos),
                'y': float(y_pos),
                'type': node_type
            })
        
        # Build edges list
        edges = []
        for i, (u, v, k) in enumerate(idx_to_edge):
            if u == v:
                continue  # Skip self-loops
            edata = G[u][v][k]
            link_type = edata.get('link_type', 'mixed')
            station_id = edata.get('station_id', None)
            edges.append({
                'id': i,
                'source': u,
                'target': v,
                'key': k,
                'linkType': link_type,
                'stationId': station_id
            })
        
        # Downsample time series for web (max 100 points)
        step = max(1, len(t_all) // 100)
        t_sampled = t_all[::step].tolist()
        x_sampled = x_all[:, ::step].tolist()
        
        # Station prices over time
        station_prices = {}
        for sid in charging_stations:
            station_prices[sid] = [get_station_parameters(t, sid, sim_t_final)['p_s'] for t in t_sampled]
        
        return {
            'nodes': nodes,
            'edges': edges,
            'timePoints': t_sampled,
            'densities': x_sampled,
            'chargingStations': {sid: int(lid) for sid, lid in charging_stations.items()},
            'stationPrices': station_prices,
            'duration': float(sim_t_final)
        }
    
    return None


# ══════════════════════════════════════════════════════
#  VISUALIZATION FUNCTIONS
# ══════════════════════════════════════════════════════
def create_network_animation(G, x_traj, t, idx_to_edge, charging_stations,
                            t_final, save_path=None, n_frames=50):
    """Create animated network visualization"""
    pos = nx.get_node_attributes(G, 'pos')
    fig, ax = plt.subplots(figsize=(14, 9))
    
    legend_elements = [
        mpatches.Patch(color='black', label='Mixed Link'),
        mpatches.Patch(color='green', label='EV Charging Link'),
        mpatches.Patch(facecolor='lightblue', edgecolor='blue', label='Origin'),
        mpatches.Patch(facecolor='lightcoral', edgecolor='red', label='Destination'),
    ]
    
    # Parallel edge map
    parallel_map = {}
    for u, v, k in G.edges(keys=True):
        parallel_map.setdefault((u, v), []).append(k)
    
    def update(frame):
        ax.clear()
        ax.set_title(f"TC9 Network: t={t[frame]:.1f}s (4 Stations)", fontsize=14, fontweight='bold')
        ax.legend(handles=legend_elements, loc='upper right', fontsize=9)
        
        # Draw nodes with different colors for origins/destinations
        for node in G.nodes():
            x_n, y_n = pos[node]
            if node.startswith('O'):
                color, ec = 'lightblue', 'blue'
            elif node.startswith('D'):
                color, ec = 'lightcoral', 'red'
            else:
                color, ec = 'lightgrey', 'black'
            ax.scatter(x_n, y_n, s=600, c=color, edgecolors=ec, linewidths=2, zorder=5)
            ax.text(x_n, y_n, node, ha='center', va='center', fontweight='bold', fontsize=10, zorder=6)
        
        # Draw edges
        for i, (u, v, k) in enumerate(idx_to_edge):
            data = G[u][v][k]
            ltype = data.get('link_type', 'mixed')
            
            if u == v:
                continue
            
            x_val = x_traj[i, frame]
            
            # Style
            color = 'green' if ltype == 'EV-only' else 'black'
            style = 'dashed' if ltype == 'EV-only' else 'solid'
            width = 1.5 + (x_val * 3.0)
            
            # Handle parallel edges
            par_keys = parallel_map.get((u, v), [])
            n_par = len(par_keys)
            idx_par = par_keys.index(k) if k in par_keys else 0
            rad = (+0.25 if idx_par == 0 else -0.25) if n_par > 1 else 0.0
            
            ax.annotate("", xy=pos[v], xytext=pos[u],
                        arrowprops=dict(arrowstyle="-|>", color=color,
                                       lw=width, linestyle=style,
                                       connectionstyle=f"arc3,rad={rad}",
                                       shrinkA=15, shrinkB=15))
            
            # Label
            x1, y1 = pos[u]
            x2, y2 = pos[v]
            mid_x, mid_y = (x1+x2)/2, (y1+y2)/2
            
            dx, dy = x2-x1, y2-y1
            norm = np.sqrt(dx**2 + dy**2)
            if norm > 0:
                perp_x, perp_y = -dy/norm, dx/norm
                sign = 1 if idx_par == 0 else -1
                off = 0.4 if n_par > 1 else 0.25
                mid_x += perp_x * off * sign
                mid_y += perp_y * off * sign
            
            if ltype == 'EV-only':
                sid = data.get('station_id', '')
                label = f"{sid}\nx:{x_val:.2f}"
                box_color = '#daffda'
                ec = 'green'
            else:
                label = f"x:{x_val:.2f}"
                box_color = 'white'
                ec = 'black'
            
            ax.text(mid_x, mid_y, label, fontsize=7, ha='center', va='center',
                   bbox=dict(boxstyle="round,pad=0.2", fc=box_color, ec=ec, alpha=0.9))
        
        ax.set_xlim(-1, 13)
        ax.set_ylim(-2, 12)
        ax.axis('off')
    
    frame_step = max(1, len(t) // n_frames)
    frames = np.arange(0, len(t), frame_step)
    ani = animation.FuncAnimation(fig, update, frames=frames, interval=100)
    
    if save_path:
        try:
            print(f"   Saving animation to {save_path}...")
            ani.save(save_path, writer='pillow', fps=10)
            print(f"   Animation saved!")
        except Exception as e:
            print(f"   Warning: Could not save animation: {e}")
    
    plt.close('all')


def od_label(od, idx_to_edge, G):
    """Get human-readable OD label"""
    u0, v0, k0 = idx_to_edge[od[0]]
    u1, v1, k1 = idx_to_edge[od[1]]
    on = G[u0][v0][k0].get('origin_id', u0)
    dn = G[u1][v1][k1].get('dest_id', u1)
    return on, dn


def plot_path_demands(t, y_EV_all, y_NEV_all, paths_EV, paths_NEV,
                     od_pairs_EV, od_pairs_NEV, lambda_EV, lambda_NEV,
                     G, idx_to_edge):
    """Plot path demand evolution"""
    plots = []

    idx = 0
    for od in od_pairs_NEV:
        np_od = len(paths_NEV[od])
        on, dn = od_label(od, idx_to_edge, G)
        plots.append(dict(title=f'NEV: {on} -> {dn}',
                         data=y_NEV_all[idx:idx+np_od, :],
                         demand=lambda_NEV[od]))
        idx += np_od

    idx = 0
    for od in od_pairs_EV:
        np_od = len(paths_EV[od])
        on, dn = od_label(od, idx_to_edge, G)
        plots.append(dict(title=f'EV: {on} -> {dn}',
                         data=y_EV_all[idx:idx+np_od, :],
                         demand=lambda_EV[od]))
        idx += np_od

    if not plots:
        return

    n_cols = 2
    n_rows = (len(plots) + 1) // 2
    fig, axs = plt.subplots(n_rows, n_cols, figsize=(14, 4*n_rows))
    fig.suptitle('Path Demand Dynamics (TC9)', fontsize=14, fontweight='bold')
    plt.subplots_adjust(hspace=0.4, wspace=0.3, top=0.92)
    axs = axs.flatten() if len(plots) > 1 else [axs]

    # Bright vibrant colors
    bright_colors = ['#1E90FF', '#FF8C00', '#32CD32', '#DC143C', '#9932CC', '#00CED1', '#FF1493']

    for i, info in enumerate(plots):
        ax = axs[i]
        for pi in range(info['data'].shape[0]):
            ax.plot(t, info['data'][pi, :], lw=2.5, label=f'Path {pi}',
                   color=bright_colors[pi % len(bright_colors)])
        ax.axhline(info['demand'], color='#DC143C', ls='--', lw=2.5,
                  label=f"Total Demand={info['demand']:.2f}")
        ax.set_title(info['title'], fontsize=11, fontweight='bold')
        ax.set_xlabel('Time')
        ax.set_ylabel('Path Flow')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)

    for i in range(len(plots), len(axs)):
        axs[i].axis('off')
    plt.show()


def plot_cost_convergence(t_all, x_all, y_EV_all, y_NEV_all,
                          paths_EV, paths_NEV,
                          od_pairs_EV, od_pairs_NEV,
                          lambda_EV, lambda_NEV, idx_to_edge, G, t_final):
    """Plot replicator convergence: tau_avg - tau_p -> 0"""
    step   = max(1, len(t_all)//400)
    t_sub  = t_all[::step]
    x_sub  = x_all[:, ::step]
    yEVs   = y_EV_all[:, ::step]
    yNEVs  = y_NEV_all[:, ::step]
    n_sub  = len(t_sub)

    # Bright colors for paths
    bright_colors = ['#1E90FF', '#FF8C00', '#32CD32', '#DC143C', '#9932CC', '#00CED1', '#FF1493']

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
                y_od = np.maximum(y_sub[pidx:pidx+np_od, ti], 0.0)
                tot  = y_od.sum()
                y_n  = y_od*(lam/tot) if tot>1e-12 else np.full(np_od, lam/np_od)
                tau_p = []
                for path in paths:
                    c = 0.0
                    for lid in path:
                        u,v,k = idx_to_edge[lid]
                        d  = G[u][v][k]
                        lt = d.get('link_type','mixed')
                        if lt in ('origin','destination'): continue
                        elif lt=='EV-only' and vcls=='EV':
                            sid = d['station_id']
                            sp  = get_station_parameters(t_sub[ti], sid, t_final)
                            xi  = x_t[lid]
                            wt  = xi / max(sp['mu_s'], 1e-9)
                            c  += latency_fn(xi,True)+alpha*wt+gamma*sp['p_s']
                        else:
                            c += latency_fn(x_t[lid])
                    tau_p.append(c)
                tau_p  = np.array(tau_p)
                tau_avg= (y_n*tau_p).sum() / max(lam,1e-12)
                gaps[:, ti] = tau_avg - tau_p
            on, dn = od_label(od, idx_to_edge, G)
            results.append(dict(title=f'{vcls}: {on}->{dn}', gaps=gaps))
            pidx += np_od
        return results

    all_res = (gap_series(od_pairs_NEV, paths_NEV, yNEVs, lambda_NEV, 'NEV') +
               gap_series(od_pairs_EV,  paths_EV,  yEVs,  lambda_EV,  'EV'))

    if not all_res: return

    n_cols = 2
    n_rows = (len(all_res)+1)//2
    fig, axs = plt.subplots(n_rows, n_cols, figsize=(16, 5*n_rows))
    fig.suptitle('Replicator Convergence:  tau_avg - tau_p  ->  0',
                 fontsize=16, fontweight='bold')
    plt.subplots_adjust(hspace=0.45, wspace=0.30, top=0.93)
    axs = axs.flatten() if len(all_res)>1 else [axs]

    for i, res in enumerate(all_res):
        ax = axs[i]
        for pi in range(res['gaps'].shape[0]):
            ax.plot(t_sub, res['gaps'][pi,:], lw=2.5, label=f'Path {pi}',
                   color=bright_colors[pi % len(bright_colors)])
        ax.axhline(0, color='#DC143C', ls='--', lw=2, label='Equilibrium (0)')
        ax.set_title(res['title'], fontsize=12, fontweight='bold')
        ax.set_xlabel('Time')
        ax.set_ylabel('tau_avg - tau_p')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8, framealpha=0.9)

    for i in range(len(all_res), len(axs)):
        axs[i].axis('off')
    plt.show()


def plot_charging_station_metrics(q_s_traj, p_s_traj, t, charging_stations, x_traj, t_final):
    """Plot charging station competition metrics"""
    station_ids = sorted(charging_stations.keys())
    # Brighter, more vibrant colors
    colors = {'S1': '#FF4136', 'S2': '#0074D9', 'S3': '#2ECC40', 'S4': '#FF851B'}

    fig, axs = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle('Competition Metrics (Dynamic Pricing Game)', fontsize=16, fontweight='bold')
    fig.patch.set_facecolor('white')

    # Scale phase boundaries
    scale = t_final / 500.0
    phases = [
        (f'Phase 1\n(0-{int(125*scale)}s)', 0, 125*scale),
        (f'Phase 2\n({int(125*scale)}-{int(250*scale)}s)', 125*scale, 250*scale),
        (f'Phase 3\n({int(250*scale)}-{int(375*scale)}s)', 250*scale, 375*scale),
        (f'Phase 4\n({int(375*scale)}-{int(t_final)}s)', 375*scale, t_final),
    ]
    x_pos = np.arange(len(phases))
    width = 0.18

    # 1 Market Share
    ax = axs[0, 0]
    tot = sum(q_s_traj[s] for s in station_ids) + 1e-9
    for sid in station_ids:
        ms = 100 * q_s_traj[sid] / tot
        ax.plot(t, ms, label=sid, lw=2.5, color=colors[sid])
        ax.fill_between(t, 0, ms, color=colors[sid], alpha=0.15)
    for _, _, pt in phases[:-1]:
        ax.axvline(pt, color='gray', ls='--', alpha=0.5, lw=1)
    ax.set_title('Market Share Evolution', fontweight='bold', fontsize=12)
    ax.set_ylabel('Market Share (%)')
    ax.set_xlabel('Time (s)')
    ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.2)
    ax.legend(fontsize=9)

    # 2 Pricing
    ax = axs[0, 1]
    for sid in station_ids:
        ax.plot(t, p_s_traj[sid], label=sid, lw=2.5, color=colors[sid])
    for _, _, pt in phases[:-1]:
        ax.axvline(pt, color='gray', ls='--', alpha=0.5, lw=1)
    ax.set_title('Pricing Strategy', fontweight='bold', fontsize=12)
    ax.set_ylabel('Price ($/vehicle)')
    ax.set_xlabel('Time (s)')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=9, framealpha=0.9)

    # 3 Queues
    ax = axs[0, 2]
    for sid in station_ids:
        lid = charging_stations[sid]
        ax.plot(t, x_traj[lid, :], label=sid, lw=2.5, color=colors[sid])
    for _, _, pt in phases[:-1]:
        ax.axvline(pt, color='gray', ls='--', alpha=0.5, lw=1)
    ax.set_title('Queue Lengths', fontweight='bold', fontsize=12)
    ax.set_ylabel('Vehicles in Queue')
    ax.set_xlabel('Time (s)')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=9, framealpha=0.9)

    # 4 Revenue by Phase
    ax = axs[1, 0]
    for i, sid in enumerate(station_ids):
        revs = []
        for _, ts, te in phases:
            mask = (t >= ts) & (t <= te)
            tp = t[mask]
            if len(tp) > 1:
                revs.append(np.trapezoid(p_s_traj[sid][mask] * q_s_traj[sid][mask], tp))
            else:
                revs.append(0.0)
        bars = ax.bar(x_pos + i*width, revs, width, label=sid, color=colors[sid], 
                     alpha=0.85, edgecolor='white', lw=1.5)
        # Add value labels on bars
        for xp, rv in zip(x_pos + i*width, revs):
            if rv > 0.05:
                ax.text(xp, rv + 0.3, f'{rv:.2f}', ha='center', va='bottom',
                       fontsize=8, fontweight='bold')
    ax.set_xticks(x_pos + width * 1.5)
    ax.set_xticklabels([p[0] for p in phases], fontsize=8)
    ax.set_ylabel('Integrated Revenue ($*veh)')
    ax.set_title('Revenue by Phase', fontweight='bold', fontsize=12)
    ax.legend(fontsize=9, framealpha=0.9)
    ax.grid(True, alpha=0.2, axis='y', ls='--')

    # 5 Net Profit
    ax = axs[1, 1]
    for i, sid in enumerate(station_ids):
        profits = []
        for _, ts, te in phases:
            mask = (t >= ts) & (t <= te)
            tp = t[mask]
            if len(tp) > 1:
                cs = np.array([get_station_parameters(ti, sid, t_final)['c_s'] for ti in tp])
                profits.append(np.trapezoid((p_s_traj[sid][mask] - cs) * q_s_traj[sid][mask], tp))
            else:
                profits.append(0.0)
        bars = ax.bar(x_pos + i*width, profits, width, label=sid, color=colors[sid], 
                     alpha=0.85, edgecolor='white', lw=1.5)
        # Add value labels on bars
        for xp, pf in zip(x_pos + i*width, profits):
            if abs(pf) > 0.05:
                ax.text(xp, pf + (0.2 if pf >= 0 else -0.4), f'{pf:.2f}', 
                       ha='center', va='bottom' if pf >= 0 else 'top',
                       fontsize=8, fontweight='bold')
    ax.set_xticks(x_pos + width * 1.5)
    ax.set_xticklabels([p[0] for p in phases], fontsize=8)
    ax.set_ylabel('Integrated Net Profit ($*veh)')
    ax.set_title('Net Profit by Phase', fontweight='bold', fontsize=12)
    ax.legend(fontsize=9, framealpha=0.9)
    ax.grid(True, alpha=0.2, axis='y', ls='--')
    ax.axhline(0, color='black', ls='-', alpha=0.3, lw=1.5)

    # 6 Overall Market Share
    ax = axs[1, 2]
    tot_int = {sid: np.trapezoid(q_s_traj[sid], t) for sid in station_ids}
    grand = sum(tot_int.values()) + 1e-9
    shares = [100 * tot_int[s] / grand for s in station_ids]
    bars = ax.bar(range(len(station_ids)), shares,
                  color=[colors[s] for s in station_ids], alpha=0.85, 
                  edgecolor='white', lw=2)
    ax.set_xticks(range(len(station_ids)))
    ax.set_xticklabels(station_ids, fontsize=12, fontweight='bold')
    ax.set_ylabel('Market Share (%)')
    ax.set_title('Overall Market Share', fontweight='bold', fontsize=12)
    ax.set_ylim(0, 110)
    ax.grid(True, alpha=0.2, axis='y', ls='--')
    for bar, pct, sid in zip(bars, shares, station_ids):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
               f'{pct:.1f}%', ha='center', va='bottom', fontweight='bold', 
               fontsize=12, color=colors[sid])

    plt.tight_layout(rect=[0, 0.02, 1, 0.96])
    plt.show()


# ──────────────────────────────────────────────────────
if __name__ == '__main__':
    run_simulation()
    print("\n" + "="*70)
    print("SIMULATION COMPLETE")
    print("="*70)
