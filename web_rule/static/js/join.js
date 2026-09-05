document.addEventListener('DOMContentLoaded', () => {
    const stepJoin = document.getElementById('step-join');
    const stepCse = document.getElementById('step-cse');
    const goCseBtn = document.getElementById('go-cse');

    stepJoin.addEventListener('click', () => {
        showPanel('join');
        if (window.optimizerState.stageData && window.optimizerState.stageData.join) {
            renderJoinStage(window.optimizerState.stageData.join);
            return;
        }
        if (!window.optimizerState.joinedPlan &&
            (window.optimizerState.pushedPlan || window.optimizerState.parsedPlan)) {
            runJoinOptimization();
        }
    });

    goCseBtn.addEventListener('click', () => {
        stepCse.disabled = false;
        showPanel('cse');
        stepCse.click();
    });

    function renderJoinStage(stage) {
        if (!stage || stage.status !== 'success') {
            const box = document.getElementById('join-error');
            box.textContent = (stage && stage.error) ? stage.error : 'Join optimization failed';
            box.classList.remove('d-none');
            return;
        }

        // Support both key names: from /analyze cache and from fetch responses
        const before = stage.original_plan  || stage.original_plan_json  || null;
        const after  = stage.optimized_plan || stage.optimized_plan_json || null;

        if (!before || !after) {
            const box = document.getElementById('join-error');
            box.textContent = 'Join stage data is incomplete.';
            box.classList.remove('d-none');
            return;
        }

        window.optimizerState.joinedPlan = after;

        const container = document.getElementById('join-result');
        renderPlanPair(container, before, after, 'Original Join Order', 'Optimized Join Order');

        // Show cost info if available
        if (stage.naive_cost !== undefined || stage.best_cost !== undefined) {
            const metricBox = document.createElement('div');
            metricBox.className = 'alert alert-info mt-3';
            metricBox.style.borderRadius = '10px';

            const naive = stage.naive_cost !== undefined ? stage.naive_cost.toFixed(2) : '—';
            const best  = stage.best_cost  !== undefined ? stage.best_cost.toFixed(2)  : '—';
            const scale = stage.cost_scale !== undefined ? ` (${(stage.cost_scale * 100).toFixed(2)}% of naive)` : '';

            const selectedOrder = Array.isArray(stage.selected_order)
                ? stage.selected_order.join(' → ')
                : '—';
            const selectedStrategies = Array.isArray(stage.selected_strategies)
                ? stage.selected_strategies.join(', ')
                : '—';

            metricBox.innerHTML = `
                <b>Exhaustive Actual Optimization</b><br>
                Naive: <code>${naive}</code> &nbsp;→&nbsp; Optimized: <code>${best}</code>${scale}
                <hr class="my-2">
                <b>Selected Plan</b><br>
                Order: <code>${selectedOrder}</code><br>
                Strategies: <code>${selectedStrategies}</code>
            `;
            container.appendChild(metricBox);

            if (stage.table_rows && Object.keys(stage.table_rows).length > 0) {
                const rowsBox = document.createElement('div');
                rowsBox.className = 'alert alert-secondary mt-2';
                rowsBox.style.borderRadius = '10px';
                const rowsHtml = Object.entries(stage.table_rows)
                    .sort((a, b) => a[0].localeCompare(b[0]))
                    .map(([table, rows]) => `<span class="me-3"><b>${table}</b>: <code>${rows}</code> rows</span>`)
                    .join('');
                rowsBox.innerHTML = `<b>Randomized Table Rows (Mock)</b><div class="mt-2">${rowsHtml}</div>`;
                container.appendChild(rowsBox);
            }

            if (stage.algorithm_results && Object.keys(stage.algorithm_results).length > 0) {
                const algoBox = document.createElement('div');
                algoBox.className = 'alert alert-light mt-2 border';
                algoBox.style.borderRadius = '10px';

                const bestAlgo = stage.most_efficient_algorithm || 'N/A';
                const bestAlgoCost = Number.isFinite(stage.most_efficient_estimated_cost)
                    ? stage.most_efficient_estimated_cost.toFixed(2)
                    : '—';

                const lines = Object.entries(stage.algorithm_results)
                    .map(([method, info]) => {
                        const cost = Number.isFinite(info.estimated_cost) ? info.estimated_cost.toFixed(2) : '—';
                        const order = Array.isArray(info.order) ? info.order.join(' → ') : '—';
                        const strategies = Array.isArray(info.strategies) ? info.strategies.join(', ') : '—';
                        const mark = method === bestAlgo ? ' <b>(best)</b>' : '';
                        return `<li><b>${method}</b>: cost <code>${cost}</code>${mark}<br><small>order: ${order} | strategies: ${strategies}</small></li>`;
                    })
                    .join('');

                algoBox.innerHTML = `
                    <b>Algorithm Comparison</b><br>
                    Most efficient: <code>${bestAlgo}</code> (estimated cost: <code>${bestAlgoCost}</code>)
                    <ul class="mt-2 mb-0">${lines}</ul>
                `;
                container.appendChild(algoBox);
            }

            if (stage.method_actual_costs && Object.keys(stage.method_actual_costs).length > 0) {
                const actualBox = document.createElement('div');
                actualBox.className = 'alert alert-warning mt-2 border';
                actualBox.style.borderRadius = '10px';

                const sortedMethods = Object.entries(stage.method_actual_costs)
                    .sort((a, b) => {
                        const aCost = Number.isFinite(a[1].actual_cost) ? a[1].actual_cost : Number.POSITIVE_INFINITY;
                        const bCost = Number.isFinite(b[1].actual_cost) ? b[1].actual_cost : Number.POSITIVE_INFINITY;
                        if (aCost === bCost) return a[0].localeCompare(b[0]);
                        return aCost - bCost;
                    });

                const bestActualMethod = sortedMethods.length ? sortedMethods[0][0] : 'N/A';
                const bestActualCost = (sortedMethods.length && Number.isFinite(sortedMethods[0][1].actual_cost))
                    ? sortedMethods[0][1].actual_cost.toFixed(2)
                    : '—';

                const exhaustiveBestCost = Number.isFinite(stage.best_cost) ? stage.best_cost.toFixed(2) : '—';
                const exhaustiveOrder = Array.isArray(stage.selected_order) ? stage.selected_order.join(' → ') : '—';
                const exhaustiveStrategies = Array.isArray(stage.selected_strategies) ? stage.selected_strategies.join(', ') : '—';
                const exhaustiveRow = `<li><b>exhaustive_actual</b>: actual <code>${exhaustiveBestCost}</code> <b>(global best)</b><br><small>order: ${exhaustiveOrder} | strategies: ${exhaustiveStrategies}</small></li>`;

                const methodRows = sortedMethods
                    .map(([method, info]) => {
                        const actual = Number.isFinite(info.actual_cost) ? info.actual_cost.toFixed(2) : '—';
                        const estimated = Number.isFinite(info.estimated_cost) ? info.estimated_cost.toFixed(2) : '—';
                        const order = Array.isArray(info.order) ? info.order.join(' → ') : '—';
                        const strategies = Array.isArray(info.strategies) ? info.strategies.join(', ') : '—';
                        const mark = method === bestActualMethod ? ' <b>(most optimized)</b>' : '';
                        const err = info.error ? `<br><small class="text-danger">error: ${info.error}</small>` : '';
                        return `<li><b>${method}</b>: actual <code>${actual}</code>${mark}, estimated <code>${estimated}</code><br><small>order: ${order} | strategies: ${strategies}</small>${err}</li>`;
                    })
                    .join('');

                actualBox.innerHTML = `
                    <b>Method Actual Cost Comparison</b><br>
                    <small>Method rows are method-selected candidates (fixed/ndv/mcv), sorted by actual cost. Best among method-selected: <code>${bestActualMethod}</code> (<code>${bestActualCost}</code>).</small>
                    <ul class="mt-2 mb-0">${exhaustiveRow}${methodRows}</ul>
                `;
                container.appendChild(actualBox);
            }

            if (stage.naive_breakdown && stage.best_breakdown) {
                const b = document.createElement('div');
                b.className = 'alert alert-primary mt-2 border';
                b.style.borderRadius = '10px';

                const nCpu = Number.isFinite(stage.naive_breakdown.cpu_cost) ? stage.naive_breakdown.cpu_cost.toFixed(2) : '—';
                const nIo = Number.isFinite(stage.naive_breakdown.io_cost) ? stage.naive_breakdown.io_cost.toFixed(2) : '—';
                const nTot = Number.isFinite(stage.naive_breakdown.total_cost) ? stage.naive_breakdown.total_cost.toFixed(2) : '—';
                const bCpu = Number.isFinite(stage.best_breakdown.cpu_cost) ? stage.best_breakdown.cpu_cost.toFixed(2) : '—';
                const bIo = Number.isFinite(stage.best_breakdown.io_cost) ? stage.best_breakdown.io_cost.toFixed(2) : '—';
                const bTot = Number.isFinite(stage.best_breakdown.total_cost) ? stage.best_breakdown.total_cost.toFixed(2) : '—';

                b.innerHTML = `
                    <b>CPU vs I/O Statistics (Naive vs Best)</b>
                    <table class="table table-sm mt-2 mb-0">
                        <thead><tr><th>Plan</th><th>Total</th><th>CPU</th><th>I/O</th></tr></thead>
                        <tbody>
                            <tr><td><b>naive</b></td><td><code>${nTot}</code></td><td><code>${nCpu}</code></td><td><code>${nIo}</code></td></tr>
                            <tr><td><b>best</b></td><td><code>${bTot}</code></td><td><code>${bCpu}</code></td><td><code>${bIo}</code></td></tr>
                        </tbody>
                    </table>
                `;
                container.appendChild(b);
            }

            if (stage.assumptions && Object.keys(stage.assumptions).length > 0) {
                const a = document.createElement('div');
                a.className = 'alert alert-secondary mt-2 border';
                a.style.borderRadius = '10px';
                const rows = Object.entries(stage.assumptions)
                    .map(([k, v]) => `<li><b>${k}</b>: <code>${typeof v === 'object' ? JSON.stringify(v) : v}</code></li>`)
                    .join('');
                a.innerHTML = `<b>Assumptions</b><ul class="mt-2 mb-0">${rows}</ul>`;
                container.appendChild(a);
            }
        } else if (stage.meta) {
            const meta = document.createElement('div');
            meta.className = 'alert alert-secondary mt-3';
            meta.style.borderRadius = '10px';
            meta.textContent = `Heuristic: ${stage.meta.heuristic || 'N/A'}`;
            container.appendChild(meta);
        }

        stepCse.disabled = false;
        goCseBtn.classList.remove('d-none');
    }

    // ─── Heuristic join (no DB needed) ───────────────────────────────────────

    function runJoinOptimization() {
        const basePlan = window.optimizerState.pushedPlan || window.optimizerState.parsedPlan;
        if (!basePlan) return;

        toggleJoinLoading(true);
        document.getElementById('join-error').classList.add('d-none');
        document.getElementById('join-result').innerHTML = '';
        goCseBtn.classList.add('d-none');

        fetch('/optimize/join/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ relational_algebra: basePlan })
        })
        .then(async r => {
            const body = await r.json().catch(() => ({}));
            if (!r.ok) throw new Error(body.error || `Server error: ${r.status} ${r.statusText}`);
            return body;
        })
        .then(data => {
            toggleJoinLoading(false);
            if (!data.success) throw new Error(data.error || 'Join optimization failed');

            window.optimizerState.joinedPlan = data.optimized_plan_json;
            window.optimizerState.stageData = window.optimizerState.stageData || {};
            window.optimizerState.stageData.join = {
                status:        'success',
                original_plan:  data.original_plan_json,
                optimized_plan: data.optimized_plan_json,
                meta:           data.meta,
            };
            renderJoinStage(window.optimizerState.stageData.join);
        })
        .catch(err => {
            toggleJoinLoading(false);
            const box = document.getElementById('join-error');
            box.textContent = err.message;
            box.classList.remove('d-none');
        });
    }

    // ─── Cost-based join (uses PostgreSQL stats) ──────────────────────────────

    window.runCostJoinOptimization = function () {
        const basePlan = window.optimizerState.pushedPlan || window.optimizerState.parsedPlan;
        if (!basePlan) {
            alert('Please run a query first (Parse step).');
            return;
        }

        toggleJoinLoading(true);
        document.getElementById('join-error').classList.add('d-none');
        document.getElementById('join-result').innerHTML = '';
        goCseBtn.classList.add('d-none');

        fetch('/optimize/join/cost', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ relational_algebra: basePlan })
        })
        .then(async r => {
            const body = await r.json().catch(() => ({}));
            if (!r.ok) throw new Error(body.error || `Server error: ${r.status} ${r.statusText}`);
            return body;
        })
        .then(data => {
            toggleJoinLoading(false);
            if (!data.success) throw new Error(data.error || 'Cost-based optimization failed');

            window.optimizerState.joinedPlan = data.optimized_plan_json;
            window.optimizerState.stageData = window.optimizerState.stageData || {};
            window.optimizerState.stageData.join = {
                status:         'success',
                original_plan:   data.original_plan_json,
                optimized_plan:  data.optimized_plan_json,
                naive_cost:      data.naive_cost,
                best_cost:       data.best_cost,
                cost_scale:      data.cost_scale,
                algorithm_results: data.algorithm_results,
                estimator_naive_cost: data.estimator_naive_cost,
                estimator_best_cost: data.estimator_best_cost,
                selected_method: data.selected_method,
                selected_order: data.selected_order,
                selected_strategies: data.selected_strategies,
                method_actual_costs: data.method_actual_costs,
                naive_breakdown: data.naive_breakdown,
                best_breakdown: data.best_breakdown,
                assumptions: data.assumptions,
                most_efficient_algorithm: data.most_efficient_algorithm,
                most_efficient_estimated_cost: data.most_efficient_estimated_cost,
                table_rows: data.table_rows,
            };
            renderJoinStage(window.optimizerState.stageData.join);
        })
        .catch(err => {
            toggleJoinLoading(false);
            const box = document.getElementById('join-error');
            box.textContent = err.message;
            box.classList.remove('d-none');
        });
    };

    function toggleJoinLoading(show) {
        document.getElementById('join-loading').classList.toggle('d-none', !show);
    }
});
