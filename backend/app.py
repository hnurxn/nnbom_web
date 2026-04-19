from flask import Flask, jsonify, request
from flask_cors import CORS
import os

from pymongo import MongoClient, ASCENDING, DESCENDING

# 创建 Flask 应用实例
app = Flask(__name__)

# 启用 CORS（跨域资源共享），允许前端跨域访问 API
CORS(app)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB = os.getenv("MONGO_DB", "nnbom_db")
MONGO_REPOS_COLLECTION = os.getenv("MONGO_REPOS_COLLECTION", "repos")
MONGO_MODULES_COLLECTION = os.getenv("MONGO_MODULES_COLLECTION", "modules")

_mongo_client = None


def get_mongo():
    global _mongo_client
    if _mongo_client is None:
        # Keep it simple; fail fast if Mongo is unreachable.
        _mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
        _mongo_client.admin.command("ping")
    db = _mongo_client[MONGO_DB]
    return db[MONGO_REPOS_COLLECTION], db[MONGO_MODULES_COLLECTION]


# ----- 简单根路由 -----
@app.route('/')
def hello():
    return 'Hello, Flask! This is the backend service.'


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
        # query params
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        sort_by = request.args.get('sort_by', 'stars').lower()
        order = request.args.get('order', 'desc')
        q = request.args.get('q', '').strip().lower()

        repos_col, modules_col = get_mongo()

        page = max(1, page)
        per_page = min(200, max(1, per_page))

        mongo_filter = {}
        if q:
            # Prefer full_name as the canonical identifier; keep description as a fallback search field.
            mongo_filter["$or"] = [
                {"full_name": {"$regex": q, "$options": "i"}},
                {"description": {"$regex": q, "$options": "i"}},
            ]

        sort_dir = DESCENDING if order == "desc" else ASCENDING
        total = repos_col.count_documents(mongo_filter)
        projection = {
            "_id": 1,
            "projectID": 1,
            "projectId": 1,
            "full_name": 1,
            "description": 1,
            "stars": 1,
            "forks": 1,
            "created_at": 1,
            "topics": 1,
            "imports": 1,
            "pretrainedModels": 1,
        }

        def to_repo_item(doc, module_count_by_project_id=None):
            project_id = doc.get("projectID", None)
            if project_id is None:
                project_id = doc.get("projectId", None)

            full_name = doc.get("full_name") or ""
            if not full_name:
                # Keep a non-empty identifier so the UI doesn't break, but treat this as a data issue.
                full_name = str(project_id if project_id is not None else doc.get("_id"))

            owner = None
            repo_name = None
            if "__" in full_name:
                owner, repo_name = full_name.split("__", 1)
            elif "/" in full_name:
                owner, repo_name = full_name.split("/", 1)
            github_url = None
            if owner and repo_name:
                github_url = f"https://github.com/{owner}/{repo_name}"

            imports = doc.get("imports") or []
            pretrained_models = doc.get("pretrainedModels") or []

            tpl_count = len(imports) if isinstance(imports, list) else 0
            ptm_count = len(pretrained_models) if isinstance(pretrained_models, list) else 0

            module_count = 0
            if project_id is not None:
                if module_count_by_project_id is not None:
                    module_count = int(module_count_by_project_id.get(project_id, 0))
                elif "moduleCount" in doc and doc.get("moduleCount") is not None:
                    module_count = int(doc.get("moduleCount") or 0)
                else:
                    module_count = modules_col.count_documents({"projectID": project_id})

            total_components = tpl_count + ptm_count + module_count

            domains = doc.get("topics")
            if not isinstance(domains, list):
                domains = []

            return {
                # full_name is the canonical identifier for NNBOM.
                "id": full_name,
                "full_name": full_name,
                # Keep "name" for frontend compatibility, but do not treat it as canonical.
                "name": full_name,
                "owner": owner,
                "repo": repo_name,
                "github_url": github_url,
                "projectID": project_id,
                "description": doc.get("description") or "",
                "stars": int(doc.get("stars") or 0),
                "forks": int(doc.get("forks") or 0),
                "created_at": doc.get("created_at") or "",
                "domains": domains,
                "components": {
                    "TPL": tpl_count,
                    "PTM": ptm_count,
                    "Module": module_count,
                    "total": total_components,
                },
            }

        page_items = []

        if sort_by in ("module", "components"):
            # Accurate sort requires module counts; compute a map once, then sort in Python.
            module_count_by_project_id = {}
            for row in modules_col.aggregate(
                [{"$group": {"_id": "$projectID", "c": {"$sum": 1}}}],
                allowDiskUse=True,
            ):
                module_count_by_project_id[row["_id"]] = row["c"]

            docs = list(repos_col.find(mongo_filter, projection))
            items = [to_repo_item(d, module_count_by_project_id) for d in docs]

            reverse = order == "desc"
            if sort_by == "module":
                items.sort(
                    key=lambda r: (r["components"]["Module"], r["full_name"]),
                    reverse=reverse,
                )
            else:
                items.sort(
                    key=lambda r: (r["components"]["total"], r["full_name"]),
                    reverse=reverse,
                )

            start = (page - 1) * per_page
            end = start + per_page
            page_items = items[start:end]
        elif sort_by in ("tpl", "ptm"):
            # Sort accurately on array sizes inside MongoDB.
            count_field = "tplCount" if sort_by == "tpl" else "ptmCount"
            src_field = "$imports" if sort_by == "tpl" else "$pretrainedModels"
            pipeline = [
                {"$match": mongo_filter},
                {"$addFields": {count_field: {"$size": {"$ifNull": [src_field, []]}}}},
                {"$sort": {count_field: sort_dir, "full_name": ASCENDING}},
                {"$skip": (page - 1) * per_page},
                {"$limit": per_page},
                {"$project": projection},
            ]
            for doc in repos_col.aggregate(pipeline, allowDiskUse=True):
                page_items.append(to_repo_item(doc))
        else:
            sort_field_map = {
                "stars": "stars",
                "forks": "forks",
                "created_at": "created_at",
                "full_name": "full_name",
            }
            sort_field = sort_field_map.get(sort_by, "stars")
            cursor = (
                repos_col.find(mongo_filter, projection)
                .sort([(sort_field, sort_dir), ("full_name", ASCENDING)])
                .skip((page - 1) * per_page)
                .limit(per_page)
            )
            for doc in cursor:
                page_items.append(to_repo_item(doc))

        return jsonify({
            'success': True,
            'total': total,
            'page': page,
            'per_page': per_page,
            'items': page_items
        })

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500



# 启动应用
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
