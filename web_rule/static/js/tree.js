class RelationalAlgebraTree {
    constructor(container) {
        this.container = container;
    }

    esc(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    render(data) {
        this.container.innerHTML = '';
        const root = document.createElement('ul');
        root.className = 'tree';
        root.appendChild(this.makeNode(data));
        this.container.appendChild(root);
        this.attachToggleHandlers();
    }

    makeNode(node) {
        const li = document.createElement('li');
        li.className = 'expanded';

        if (this.hasChildren(node)) {
            const toggle = document.createElement('span');
            toggle.className = 'toggle-btn';
            li.appendChild(toggle);
        }

        const box = document.createElement('div');
        box.className = 'tree-node';
        box.innerHTML = `<span class="tree-node-type">${this.icon(node.type)} ${this.label(node.type)}</span>`;

        const detail = document.createElement('span');
        detail.className = 'tree-node-detail';
        detail.innerHTML = this.detail(node);
        if (detail.innerHTML) box.appendChild(detail);
        li.appendChild(box);

        if (this.hasChildren(node)) {
            const ul = document.createElement('ul');
            ['input', 'left', 'right', 'query'].forEach(key => {
                if (node[key]) ul.appendChild(this.makeNode(node[key]));
            });
            li.appendChild(ul);
        }
        return li;
    }

    hasChildren(node) {
        return !!(node && (node.input || node.left || node.right || node.query));
    }

    label(type) {
        const map = {
            project: 'PROJECT', select: 'SELECT', join: 'JOIN', base_relation: 'TABLE', subquery: 'SUBQUERY'
        };
        return map[type] || String(type || 'NODE').toUpperCase();
    }

    icon(type) {
        const map = { project: '📏', select: '🔍', join: '🔗', base_relation: '📋', subquery: '🧩' };
        return map[type] || '⚙️';
    }

    detail(node) {
        if (!node) return '';
        if (node.type === 'base_relation' && node.tables) {
            return ': ' + node.tables.map(t => {
                const name = `<span class="tree-table">${this.esc(t.name)}</span>`;
                if (!t.alias) return name;
                return `${name} AS <span class="tree-table">${this.esc(t.alias)}</span>`;
            }).join(', ');
        }
        if (node.type === 'project' && node.columns) {
            return ': ' + node.columns.map(c => {
                if (c.table) {
                    return `<span class="tree-column">${this.esc(c.table)}.${this.esc(c.attr)}</span>`;
                }
                return `<span class="tree-column">${this.esc(c.attr)}</span>`;
            }).join(', ');
        }
        if ((node.type === 'select' || node.type === 'join') && node.condition) {
            return ': <span class="tree-node-condition">' + this.cond(node.condition) + '</span>';
        }
        if (node.type === 'subquery' && node.alias) {
            return `: <span class="tree-table">${this.esc(node.alias)}</span>`;
        }
        return '';
    }

    cond(c) {
        if (!c) return '';
        if (c.table && c.attr) return `<span class="tree-column">${this.esc(c.table)}.${this.esc(c.attr)}</span>`;
        if (c.type === 'column') {
            if (c.table) return `<span class="tree-column">${this.esc(c.table)}.${this.esc(c.attr)}</span>`;
            return `<span class="tree-column">${this.esc(c.attr)}</span>`;
        }
        if (c.type === 'int' || c.type === 'float') return `<span class="tree-literal">${this.esc(c.value)}</span>`;
        if (c.type === 'string') return `<span class="tree-literal">'${this.esc(c.value)}'</span>`;
        if (c.type === 'NOT') return `NOT (${this.cond(c.cond)})`;
        if (c.left && c.right) {
            const op = { EQ:'=', LT:'<', GT:'>', LE:'<=', GE:'>=', NE:'<>', AND:'AND', OR:'OR' }[c.type] || c.type;
            return `(${this.cond(c.left)} <span class="tree-operator">${this.esc(op)}</span> ${this.cond(c.right)})`;
        }
        return this.esc(JSON.stringify(c));
    }

    attachToggleHandlers() {
        this.container.querySelectorAll('.toggle-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const li = btn.parentElement;
                li.classList.toggle('expanded');
                li.classList.toggle('collapsed');
            });
        });
    }
}
