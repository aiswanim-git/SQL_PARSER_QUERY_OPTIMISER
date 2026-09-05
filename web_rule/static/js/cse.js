document.addEventListener('DOMContentLoaded', () => {
    const stepCse = document.getElementById('step-cse');
    const finishBtn = document.getElementById('finish-flow');

    stepCse.addEventListener('click', () => {
        showPanel('cse');
        if (window.optimizerState.stageData && window.optimizerState.stageData.cse) {
            renderCseStage(window.optimizerState.stageData.cse);
            return;
        }
        if (!window.optimizerState.csePlan && (window.optimizerState.joinedPlan || window.optimizerState.pushedPlan || window.optimizerState.parsedPlan)) {
            runCse();
        }
    });

    function renderCseStage(stage) {
        if (!stage || stage.status !== 'success') {
            const box = document.getElementById('cse-error');
            box.textContent = stage && stage.error ? stage.error : 'Common subexpression elimination failed';
            box.classList.remove('d-none');
            return;
        }
        // Support both key names
        const before = stage.original_plan  || stage.original_plan_json  || null;
        const after  = stage.optimized_plan || stage.optimized_plan_json || null;
        if (!before || !after) {
            const box = document.getElementById('cse-error');
            box.textContent = 'CSE stage data is incomplete.';
            box.classList.remove('d-none');
            return;
        }
        window.optimizerState.csePlan = after;
        const resultBox = document.getElementById('cse-result');
        renderPlanPair(
            resultBox,
            before,
            after,
            'Before CSE',
            'After CSE Scan'
        );
        const info = document.createElement('div');
        info.className = 'alert alert-secondary mt-3';
        info.style.borderRadius = '10px';
        const count = stage.meta && typeof stage.meta.duplicate_count === 'number' ? stage.meta.duplicate_count : 0;
        info.textContent = `Detected repeated subexpressions: ${count}`;
        resultBox.appendChild(info);
        finishBtn.classList.remove('d-none');
    }

    function runCse() {
        const basePlan = window.optimizerState.joinedPlan || window.optimizerState.pushedPlan || window.optimizerState.parsedPlan;
        document.getElementById('cse-loading').classList.remove('d-none');
        document.getElementById('cse-error').classList.add('d-none');
        finishBtn.classList.add('d-none');

        fetch('/optimize/common_subexpr/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ relational_algebra: basePlan })
        })
        .then(r => {
            if (!r.ok) throw new Error(`Server error: ${r.status} ${r.statusText}`);
            return r.json();
        })
        .then(data => {
            document.getElementById('cse-loading').classList.add('d-none');
            if (!data.success) throw new Error(data.error || 'Common subexpression elimination failed');
            window.optimizerState.csePlan = data.optimized_plan_json;
            window.optimizerState.stageData = window.optimizerState.stageData || {};
            // Store with consistent keys
            window.optimizerState.stageData.cse = {
                status: 'success',
                original_plan:  data.original_plan_json,
                optimized_plan: data.optimized_plan_json,
                meta: data.meta,
            };
            renderPlanPair(
                document.getElementById('cse-result'),
                data.original_plan_json,
                data.optimized_plan_json,
                'Before CSE',
                'After CSE Scan'
            );
            const info = document.createElement('div');
            info.className = 'alert alert-secondary mt-3';
            info.style.borderRadius = '10px';
            const count = data.meta && typeof data.meta.duplicate_count === 'number' ? data.meta.duplicate_count : 0;
            info.textContent = `Detected repeated subexpressions: ${count}`;
            document.getElementById('cse-result').appendChild(info);
            finishBtn.classList.remove('d-none');
        })
        .catch(err => {
            document.getElementById('cse-loading').classList.add('d-none');
            const box = document.getElementById('cse-error');
            box.textContent = err.message;
            box.classList.remove('d-none');
        });
    }

    finishBtn.addEventListener('click', () => {
        if (typeof window.launchCelebration === 'function') {
            window.launchCelebration();
        }
    });
});
