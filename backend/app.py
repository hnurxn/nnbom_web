from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import random
from datetime import datetime, timedelta

# 创建 Flask 应用实例
app = Flask(__name__)

# 启用 CORS（跨域资源共享），允许前端跨域访问 API
CORS(app)


# ----- 简单根路由 -----
@app.route('/')
def hello():
    return 'Hello, Flask! This is the backend service.'


# ----- 仓库数据生成（内存） -----
# 为了快速构建首页展示，我们在内存中生成随机示例数据（约 50k 条）
REPO_STORE = None

def generate_repos(n=50000, seed=42):
    """生成 n 条示例仓库元信息，包含三个 component: TPL, PTM, Module"""
    random.seed(seed)
    base_date = datetime(2018, 1, 1)
    repos = []
    langs = ['Python', 'C++', 'C', 'JavaScript', 'Lua', 'Rust']
    domain_pool = ['CV', 'NLP', 'Robotics', 'Healthcare', 'Finance', 'Education', 'Audio', 'Reinforcement']
    for i in range(n):
        name = f'nnbom-repo-{i+1:05d}'
        stars = random.randint(0, 5000)
        forks = random.randint(0, 2000)
        days = random.randint(0, 2500)
        created_at = (base_date + timedelta(days=days)).strftime('%Y-%m-%d')
        language = random.choice(langs)

        # components counts
        tpl = random.randint(0, 200)
        ptm = random.randint(0, 200)
        module = random.randint(0, 200)
        total_components = tpl + ptm + module

        domains = random.sample(domain_pool, random.randint(1, min(3, len(domain_pool))))

        repos.append({
            'id': i+1,
            'name': name,
            'description': f'自动生成示例仓库 {name}',
            'stars': stars,
            'forks': forks,
            'created_at': created_at,
            'language': language,
            'domains': domains,
            'components': {
                'TPL': tpl,
                'PTM': ptm,
                'Module': module,
                'total': total_components
            }
        })
    return repos


def ensure_repo_store():
    global REPO_STORE
    if REPO_STORE is None:
        # 生成 50000 条数据，注意：首次生成可能需要数秒
        REPO_STORE = generate_repos(n=50000)
    return REPO_STORE


# ----- API: 获取仓库列表（分页、排序、搜索） -----
@app.route('/api/repos')
def api_repos():
    """
    Query params:
      - page (int, default=1)
      - per_page (int, default=20)
      - sort_by (tpl|ptm|module|stars|created_at|components, default=stars)
      - order (asc|desc, default=desc)
      - q (search string in name)
    """
    try:
        repos = ensure_repo_store()

        # query params
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        sort_by = request.args.get('sort_by', 'stars').lower()
        order = request.args.get('order', 'desc')
        q = request.args.get('q', '').strip().lower()

        # filter
        filtered = repos
        if q:
            filtered = [r for r in repos if q in r['name'].lower() or q in r['description'].lower()]

        # sort
        reverse = (order == 'desc')
        if sort_by == 'stars':
            filtered.sort(key=lambda r: r['stars'], reverse=reverse)
        elif sort_by == 'created_at':
            filtered.sort(key=lambda r: r['created_at'], reverse=reverse)
        elif sort_by == 'components':
            filtered.sort(key=lambda r: r['components']['total'], reverse=reverse)
        elif sort_by in ('tpl', 'ptm', 'module'):
            comp_map = {
                'tpl': 'TPL',
                'ptm': 'PTM',
                'module': 'Module'
            }
            key_name = comp_map[sort_by]
            filtered.sort(key=lambda r: r['components'][key_name], reverse=reverse)

        total = len(filtered)

        # paginate
        start = (page - 1) * per_page
        end = start + per_page
        page_items = filtered[start:end]

        return jsonify({
            'success': True,
            'total': total,
            'page': page,
            'per_page': per_page,
            'items': page_items
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ----- 保留旧的 Excel 接口（如果需要） -----
@app.route('/api/excel-data')
def get_excel_data():
    # 如果项目中仍需要读取 backend/data.xlsx，保留此接口
    current_dir = os.path.dirname(os.path.abspath(__file__))
    excel_path = os.path.join(current_dir, 'data.xlsx')
    if not os.path.exists(excel_path):
        return jsonify({'success': False, 'message': 'Excel 文件不存在'}), 404
    try:
        import pandas as pd
        df = pd.read_excel(excel_path, sheet_name=0)
        data = df.to_dict('records')
        columns = list(df.columns)
        return jsonify({'success': True, 'columns': columns, 'data': data, 'total': len(data)})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# 启动应用
if __name__ == '__main__':
    # 注意：首次运行会在内存中生成约 50k 条示例数据，可能需要几秒钟
    app.run(debug=True, host='0.0.0.0', port=5001)
