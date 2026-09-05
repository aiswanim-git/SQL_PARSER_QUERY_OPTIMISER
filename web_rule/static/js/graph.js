class RelationalAlgebraGraph {
    constructor(container) {
        this.container = container;
        this.commonExpressions = {};
        this.sharedRefs = [];
        this.sharedRoots = {};
    }

    _kind(node) {
        const type = String((node && node.type) || '').toLowerCase();
        if (type === 'project') return 'project';
        if (type === 'select') return 'select';
        if (type === 'join') return 'join';
        if (type === 'base_relation') return 'table';
        if (type === 'subquery') return 'subquery';
        if (type === 'expr_ref') return 'expr_ref';
        return 'other';
    }

    _rawChildren(node) {
        const keys = ['input', 'left', 'right', 'query', 'child'];
        return keys
            .map(key => node && node[key])
            .filter(value => value && typeof value === 'object');
    }

    _symbol(kind) {
        return {
            project: '\u03c0',
            select: '\u03c3',
            join: '\u22c8',
        }[kind] || '';
    }

    _formatValue(value) {
        if (!value) return '';
        if (typeof value === 'string') return value;
        if (value.type === 'int' || value.type === 'float') return String(value.value);
        if (value.type === 'string') return String(value.value);
        if (value.table && value.attr) return `${value.table}.${value.attr}`;
        if (value.attr) return value.attr;
        if (value.left && value.right) {
            return `${this._formatValue(value.left)} ${this._opLabel(value.type)} ${this._formatValue(value.right)}`;
        }
        return '';
    }

    _opLabel(op) {
        return {
            EQ: '=',
            NE: '!=',
            LT: '<',
            LE: '<=',
            GT: '>',
            GE: '>=',
            AND: 'AND',
            OR: 'OR',
        }[op] || op || '';
    }

    _formatCondition(condition) {
        if (!condition) return '';
        if (typeof condition === 'string') return condition;
        if (condition.type === 'NOT') return `NOT ${this._formatCondition(condition.cond)}`;
        if (condition.left && condition.right) {
            return `${this._formatValue(condition.left)} ${this._opLabel(condition.type)} ${this._formatValue(condition.right)}`;
        }
        return '';
    }

    _label(node, kind) {
        if (kind === 'project') {
            const cols = (node.columns || []).map(col => {
                if (typeof col === 'string') return col;
                if (col.table) return `${col.table}.${col.attr}`;
                return col.attr || '*';
            }).join(', ');
            return `${this._symbol(kind)} ${cols}`.trim();
        }
        if (kind === 'select') {
            return `${this._symbol(kind)} ${this._formatCondition(node.condition)}`.trim();
        }
        if (kind === 'join') {
            return `${this._symbol(kind)} ${this._formatCondition(node.condition)}`.trim();
        }
        if (kind === 'table') {
            const table = (node.tables || [])[0] || {};
            const name = String(table.name || 'TABLE');
            const alias = table.alias ? String(table.alias) : '';
            return alias ? `${name} AS ${alias}` : name;
        }
        if (kind === 'subquery') {
            return String(node.alias || 'SUBQUERY');
        }
        return String(node.type || 'NODE').toUpperCase();
    }

    _wrapLabel(label, maxChars = 24) {
        if (!label) return [''];
        const words = String(label).split(/\s+/);
        const lines = [];
        let current = '';

        for (const word of words) {
            const next = current ? `${current} ${word}` : word;
            if (next.length > maxChars && current) {
                lines.push(current);
                current = word;
            } else {
                current = next;
            }
        }

        if (current) lines.push(current);
        return lines.length ? lines : [''];
    }

    _style(kind) {
        const styles = {
            project:  { fill: '#ffffff', stroke: '#4f46e5', text: '#3730a3', font: 'Georgia, serif', weight: 700 },
            select:   { fill: '#ffffff', stroke: '#16a34a', text: '#15803d', font: 'Georgia, serif', weight: 700 },
            join:     { fill: '#ffffff', stroke: '#2563eb', text: '#1d4ed8', font: 'Georgia, serif', weight: 700 },
            table:    { fill: '#dcfce7', stroke: '#15803d', text: '#14532d', font: 'Georgia, serif', weight: 700 },
            subquery: { fill: '#f3e8ff', stroke: '#7e22ce', text: '#581c87', font: 'Georgia, serif', weight: 700 },
            expr_ref: { fill: '#ffffff', stroke: '#6b7280', text: '#374151', font: 'Georgia, serif', weight: 700 },
            other:    { fill: '#ffffff', stroke: '#6b7280', text: '#374151', font: 'Georgia, serif', weight: 700 },
        };
        return styles[kind] || styles.other;
    }

    _size(item) {
        const label = this._label(item.node, item.kind);
        const lines = this._wrapLabel(label, item.kind === 'project' ? 28 : 24);
        const maxLine = Math.max(...lines.map(line => line.length), 6);
        const widthBase = item.kind === 'table' || item.kind === 'subquery' ? 28 : 40;
        const width = Math.max(
            item.kind === 'table' || item.kind === 'subquery' ? 96 : 128,
            Math.min(300, maxLine * 10 + widthBase)
        );
        const lineHeight = 19;
        const height = Math.max(
            item.kind === 'table' || item.kind === 'subquery' ? 52 : 50,
            22 + lines.length * lineHeight
        );
        return { width, height, lines, lineHeight };
    }

    _build(node, depth = 0) {
        if (!node || typeof node !== 'object') return null;
        if (String(node.type || '').toLowerCase() === 'expr_ref') return null;
        const kind = this._kind(node);
        const children = [];
        for (const child of this._rawChildren(node)) {
            if (String(child.type || '').toLowerCase() === 'expr_ref') {
                const exprId = child.id;
                if (exprId && this.commonExpressions[exprId]) {
                    this.sharedRefs.push({ fromNode: node, exprId });
                }
                continue;
            }
            const built = this._build(child, depth + 1);
            if (built) children.push(built);
        }
        const baseWidth = this._size({ node, kind }).width + 44;
        const subtreeWidth = children.length
            ? Math.max(baseWidth, children.reduce((sum, child) => sum + child.subtreeWidth, 0))
            : baseWidth;
        return { node, kind, depth, children, subtreeWidth };
    }

    _position(item, offsetX) {
        item.x = offsetX + item.subtreeWidth / 2;
        item.y = RelationalAlgebraGraph.PAD_Y + item.depth * RelationalAlgebraGraph.LEVEL_GAP;
        let cursor = offsetX;
        for (const child of item.children) {
            this._position(child, cursor);
            cursor += child.subtreeWidth;
        }
    }

    _flatten(item, out = []) {
        if (!item) return out;
        out.push(item);
        item.children.forEach(child => this._flatten(child, out));
        return out;
    }

    _flattenUnique(items) {
        const seen = new Set();
        const out = [];
        const walk = item => {
            if (!item || seen.has(item)) return;
            seen.add(item);
            out.push(item);
            item.children.forEach(walk);
        };
        items.forEach(walk);
        return out;
    }

    _buildSharedRoots(startDepth) {
        const exprIds = [...new Set(this.sharedRefs.map(ref => ref.exprId))]
            .filter(exprId => this.commonExpressions[exprId]);
        this.sharedRoots = {};
        return exprIds.map(exprId => {
            const root = this._build(this.commonExpressions[exprId], startDepth);
            if (root) {
                this.sharedRoots[exprId] = root;
            }
            return root;
        }).filter(Boolean);
    }

    _positionSharedRoots(roots, offsetX) {
        let cursor = offsetX;
        roots.forEach(root => {
            this._position(root, cursor);
            cursor += root.subtreeWidth + 36;
        });
        return cursor;
    }

    _referenceEdge(parent, child) {
        const parentSize = this._size(parent);
        const childSize = this._size(child);
        const x1 = parent.x;
        const y1 = parent.y + parentSize.height / 2;
        const x2 = child.x;
        const y2 = child.y - childSize.height / 2;
        return `<path d="M ${x1} ${y1} C ${x1} ${y1 + 20}, ${x2} ${y2 - 20}, ${x2} ${y2}"
            fill="none" stroke="#94a3b8" stroke-width="2.4"
            stroke-linecap="round" stroke-linejoin="round"/>`;
    }

    _edge(parent, child) {
        const parentSize = this._size(parent);
        const childSize = this._size(child);
        const x1 = parent.x;
        const y1 = parent.y + parentSize.height / 2;
        const x2 = child.x;
        const y2 = child.y - childSize.height / 2;
        const midY = (y1 + y2) / 2;
        return `<path d="M ${x1} ${y1} L ${x1} ${midY} L ${x2} ${midY} L ${x2} ${y2}"
            fill="none" stroke="#94a3b8" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>`;
    }

    _node(item) {
        const style = this._style(item.kind);
        const size = this._size(item);
        const x = item.x - size.width / 2;
        const y = item.y - size.height / 2;
        const radius = item.kind === 'table' || item.kind === 'subquery' ? 12 : 10;
        const shadow = item.kind === 'table' || item.kind === 'subquery' ? 'url(#leafShadow)' : 'url(#boxShadow)';
        const textLines = size.lines.map((line, index) => {
            const totalTextHeight = size.lines.length * size.lineHeight;
            const baseY = item.y - totalTextHeight / 2 + size.lineHeight * 0.82;
            return `<text x="${item.x}" y="${baseY + index * size.lineHeight}"
                text-anchor="middle"
                font-size="${index === 0 ? 14 : 12}"
                font-weight="${style.weight}"
                fill="${style.text}"
                font-family="${style.font}">${this._escape(line)}</text>`;
        }).join('');

        return `<g class="qt-node qt-${item.kind}">
            <rect x="${x}" y="${y}" width="${size.width}" height="${size.height}"
                rx="${radius}" ry="${radius}"
                fill="${style.fill}" stroke="${style.stroke}" stroke-width="2.2"
                filter="${shadow}"/>
            ${textLines}
        </g>`;
    }

    _escape(value) {
        return String(value || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    render(data) {
        this.container.innerHTML = '';
        this.sharedRefs = [];
        this.sharedRoots = {};
        this.commonExpressions = (data && typeof data === 'object' && data.common_expressions) || {};

        if (!data || typeof data !== 'object') {
            this.container.innerHTML = '<p class="text-muted p-3 small">No graph data.</p>';
            return;
        }

        const rootNode = (data.query && typeof data.query === 'object') ? data.query : data;
        const root = this._build(rootNode);
        if (!root) {
            this.container.innerHTML = '<p class="text-muted p-3 small">Cannot render tree.</p>';
            return;
        }

        this._position(root, RelationalAlgebraGraph.PAD_X);
        const mainNodes = this._flatten(root);
        const mainMaxDepth = mainNodes.reduce((max, item) => Math.max(max, item.depth), 0);
        const sharedRoots = this._buildSharedRoots(mainMaxDepth + 2);
        this._positionSharedRoots(sharedRoots, RelationalAlgebraGraph.PAD_X);
        const nodes = this._flattenUnique([root, ...sharedRoots]);

        let maxWidth = 0;
        let maxHeight = 0;
        for (const item of nodes) {
            const size = this._size(item);
            maxWidth = Math.max(maxWidth, item.x + size.width / 2 + RelationalAlgebraGraph.PAD_X);
            maxHeight = Math.max(maxHeight, item.y + size.height / 2 + RelationalAlgebraGraph.PAD_Y);
        }

        const treeEdges = nodes
            .flatMap(item => item.children.map(child => this._edge(item, child)))
            .join('');
        const refEdges = this.sharedRefs
            .map(ref => {
                const from = nodes.find(item => item.node === ref.fromNode);
                const to = this.sharedRoots[ref.exprId];
                if (!from || !to) return '';
                return this._referenceEdge(from, to);
            })
            .join('');
        const nodeMarkup = nodes.map(item => this._node(item)).join('');

        const svg = `<svg xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 ${maxWidth} ${maxHeight}"
            width="100%"
            height="${Math.max(420, maxHeight)}"
            style="display:block;border-radius:16px;background:linear-gradient(180deg,#f8fbff 0%,#eef2ff 100%)">
            <defs>
                <filter id="boxShadow" x="-20%" y="-30%" width="140%" height="170%">
                    <feDropShadow dx="0" dy="2" stdDeviation="2" flood-color="#00000012"/>
                </filter>
                <filter id="leafShadow" x="-20%" y="-30%" width="140%" height="170%">
                    <feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#00000018"/>
                </filter>
            </defs>
            <g class="qt-edges">${treeEdges}${refEdges}</g>
            <g class="qt-nodes">${nodeMarkup}</g>
        </svg>`;

        const wrapper = document.createElement('div');
        wrapper.className = 'qt-graph-wrapper';
        wrapper.innerHTML = svg;
        this.container.appendChild(wrapper);
    }
}

RelationalAlgebraGraph.PAD_X = 36;
RelationalAlgebraGraph.PAD_Y = 36;
RelationalAlgebraGraph.LEVEL_GAP = 112;
