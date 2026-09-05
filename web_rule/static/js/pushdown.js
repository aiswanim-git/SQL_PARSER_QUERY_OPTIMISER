window.optimizerState = window.optimizerState || {
    parsedPlan: null,
    pushedPlan: null,
    joinedPlan: null,
    csePlan: null,
    stageData: {
        pushdown: null,
        join: null,
        cse: null,
    },
};

function showPanel(step) {
    const steps = ['parse', 'pushdown', 'join', 'cse'];
    steps.forEach(name => {
        document.getElementById(`panel-${name}`).classList.toggle('active', name === step);
        document.getElementById(`step-${name}`).classList.toggle('active', name === step);
    });
}

function planViewerMarkup(title) {
    return `
        <div class="border rounded p-3 bg-white h-100">
            <div class="d-flex align-items-center justify-content-between flex-wrap gap-2 mb-3">
                <h5 class="mb-0">${title}</h5>
                <div class="view-tabs mb-0">
                    <button class="view-mode" data-mode="json"><i class="bi bi-filetype-json me-1"></i>JSON</button>
                    <button class="view-mode" data-mode="tree"><i class="bi bi-list-nested me-1"></i>Text Tree</button>
                    <button class="view-mode active" data-mode="graph"><i class="bi bi-diagram-2 me-1"></i>Graph</button>
                </div>
            </div>
            <div class="plan-json d-none"><pre class="small bg-light p-2 rounded mb-0"></pre></div>
            <div class="plan-tree d-none"></div>
            <div class="plan-graph"></div>
        </div>
    `;
}

function renderPlanViewer(viewer, plan) {
    const graphContainer = viewer.querySelector('.plan-graph');
    const treeContainer = viewer.querySelector('.plan-tree');
    const jsonContainer = viewer.querySelector('.plan-json');
    const jsonPre = jsonContainer.querySelector('pre');
    const viewMap = {
        json: jsonContainer,
        tree: treeContainer,
        graph: graphContainer,
    };

    jsonPre.textContent = JSON.stringify(plan, null, 2);
    new RelationalAlgebraTree(treeContainer).render(plan);
    new RelationalAlgebraGraph(graphContainer).render(plan);

    function setMode(mode) {
        Object.entries(viewMap).forEach(([key, node]) => {
            node.classList.toggle('d-none', key !== mode);
        });
        viewer.querySelectorAll('.view-mode').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.mode === mode);
        });
    }

    viewer.querySelectorAll('.view-mode').forEach(btn => {
        btn.addEventListener('click', () => setMode(btn.dataset.mode));
    });

    setMode('graph');
}

function renderPlanPair(container, beforePlan, afterPlan, beforeTitle, afterTitle) {
    container.innerHTML = `
        <div class="row g-3">
            <div class="col-md-6">
                <div class="plan-viewer before-plan-viewer">
                    ${planViewerMarkup(beforeTitle)}
                </div>
            </div>
            <div class="col-md-6">
                <div class="plan-viewer after-plan-viewer">
                    ${planViewerMarkup(afterTitle)}
                </div>
            </div>
        </div>
    `;
    renderPlanViewer(container.querySelector('.before-plan-viewer'), beforePlan);
    renderPlanViewer(container.querySelector('.after-plan-viewer'), afterPlan);
}

document.addEventListener('DOMContentLoaded', () => {
    const goBtn = document.getElementById('go-optimize');
    const goJoinBtn = document.getElementById('go-join');
    const stepPush = document.getElementById('step-pushdown');
    const stepJoin = document.getElementById('step-join');
    const stepCse = document.getElementById('step-cse');
    const stepParse = document.getElementById('step-parse');

    stepParse.addEventListener('click', () => showPanel('parse'));
    stepPush.addEventListener('click', () => {
        showPanel('pushdown');
        if (window.optimizerState.stageData && window.optimizerState.stageData.pushdown) {
            renderPushdownStage(window.optimizerState.stageData.pushdown);
            if (window.optimizerState.joinedPlan) {
                stepJoin.disabled = false;
            }
            return;
        }
        if (!window.optimizerState.pushedPlan && window.optimizerState.parsedPlan) runPushdown();
    });

    goBtn.addEventListener('click', () => {
        showPanel('pushdown');
        if (window.optimizerState.stageData && window.optimizerState.stageData.pushdown) {
            renderPushdownStage(window.optimizerState.stageData.pushdown);
            return;
        }
        runPushdown();
    });

    goJoinBtn.addEventListener('click', () => {
        stepJoin.disabled = false;
        showPanel('join');
        stepJoin.click();
    });

    function renderPushdownStage(stage) {
        if (!stage || stage.status !== 'success') {
            const box = document.getElementById('pushdown-error');
            box.textContent = stage && stage.error ? stage.error : 'Predicate pushdown failed';
            box.classList.remove('d-none');
            return;
        }
        // Support both key names: from /analyze cache and from /optimize/pred_push/ response
        const before = stage.original_plan  || stage.original_plan_json  || null;
        const after  = stage.optimized_plan || stage.optimized_plan_json || null;
        if (!before || !after) {
            const box = document.getElementById('pushdown-error');
            box.textContent = 'Pushdown stage data is incomplete.';
            box.classList.remove('d-none');
            return;
        }
        window.optimizerState.pushedPlan = after;
        renderPlanPair(
            document.getElementById('pushdown-result'),
            before,
            after,
            'Before Pushdown',
            'After Pushdown'
        );
        goJoinBtn.classList.remove('d-none');
        stepJoin.disabled = false;
    }

    function runPushdown() {
        if (!window.optimizerState.parsedPlan) return;
        document.getElementById('pushdown-loading').classList.remove('d-none');
        document.getElementById('pushdown-error').classList.add('d-none');
        goJoinBtn.classList.add('d-none');

        fetch('/optimize/pred_push/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ relational_algebra: window.optimizerState.parsedPlan })
        })
        .then(r => {
            if (!r.ok) throw new Error(`Server error: ${r.status} ${r.statusText}`);
            return r.json();
        })
        .then(data => {
            document.getElementById('pushdown-loading').classList.add('d-none');
            if (!data.success) throw new Error(data.error || 'Predicate pushdown failed');
            window.optimizerState.pushedPlan = data.optimized_plan_json;
            window.optimizerState.stageData = window.optimizerState.stageData || {};
            // Store with consistent keys
            window.optimizerState.stageData.pushdown = {
                status: 'success',
                original_plan:  data.original_plan_json,
                optimized_plan: data.optimized_plan_json,
            };
            renderPlanPair(
                document.getElementById('pushdown-result'),
                data.original_plan_json,
                data.optimized_plan_json,
                'Before Pushdown',
                'After Pushdown'
            );
            goJoinBtn.classList.remove('d-none');
            stepJoin.disabled = false;
        })
        .catch(err => {
            document.getElementById('pushdown-loading').classList.add('d-none');
            const box = document.getElementById('pushdown-error');
            box.textContent = err.message;
            box.classList.remove('d-none');
        });
    }
});
