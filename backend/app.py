from flask import Flask, jsonify, request
from flask_cors import CORS
import os

from pymongo import MongoClient, ASCENDING, DESCENDING
from datetime import datetime, timezone

# 创建 Flask 应用实例
app = Flask(__name__)

# 启用 CORS（跨域资源共享），允许前端跨域访问 API
CORS(app)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB = os.getenv("MONGO_DB", "nnbom_db")
MONGO_REPOS_COLLECTION = os.getenv("MONGO_REPOS_COLLECTION", "repos")
MONGO_MODULES_COLLECTION = os.getenv("MONGO_MODULES_COLLECTION", "modules")

_mongo_client = None


def get_db():
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
        _mongo_client.admin.command("ping")
    return _mongo_client[MONGO_DB]


def get_mongo():
    db = get_db()
    return db[MONGO_REPOS_COLLECTION], db[MONGO_MODULES_COLLECTION]

def _clamp_int(value, default=20, min_value=1, max_value=200):
    try:
        n = int(value)
    except Exception:
        n = int(default)
    return max(min_value, min(max_value, n))


def _module_key_expr():
    # Best-effort normalize different module schemas into a stable string key.
    # Keep this purely in aggregation expressions so it can be used in pipelines.
    return {
        "$toString": {
            "$ifNull": [
                "$module_name",
                {
                    "$ifNull": [
                        "$moduleName",
                        {
                            "$ifNull": [
                                "$name",
                                {
                                    "$ifNull": [
                                        "$module",
                                        {"$ifNull": ["$moduleID", {"$ifNull": ["$moduleId", "$id"]}]},
                                    ]
                                },
                            ]
                        },
                    ]
                },
            ]
        }
    }


def _project_id_expr():
    return {"$ifNull": ["$projectID", "$projectId"]}


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


@app.route("/api/stats/summary")
def api_stats_summary():
    """Read precomputed global stats from MongoDB collection `stats`."""
    try:
        db = get_db()
        stats_col = db["stats"]

        doc = stats_col.find_one({"_id": "global_stats"})
        if not doc:
            return jsonify({"success": False, "message": "stats not found (_id=global_stats)"}), 404

        last_updated = doc.get("last_updated")
        if isinstance(last_updated, datetime):
            if last_updated.tzinfo is None:
                last_updated = last_updated.replace(tzinfo=timezone.utc)
            last_updated = last_updated.replace(microsecond=0).isoformat().replace("+00:00", "Z")

        payload = {
            "total_tpl": int(doc.get("total_tpl") or 0),
            "total_ptm": int(doc.get("total_ptm") or 0),
            "total_module": int(doc.get("total_module") or 0),
            "total_dependency": int(doc.get("total_dependency") or 0),
            "last_updated": last_updated,
        }
        return jsonify({"success": True, "stats": payload})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/analytics/summary")
def api_analytics_summary():
    """
    Dataset-level analytics summary for the Analytics page.
    Returns:
      - total_repos, unique_tpl, unique_ptm, unique_module
      - last_updated (from stats collection when available)
    """
    try:
        repos_col, modules_col = get_mongo()

        total_repos = repos_col.count_documents({})

        tpl_unique_pipeline = [
            {"$project": {"imports": {"$ifNull": ["$imports", []]}}},
            {"$unwind": "$imports"},
            {"$addFields": {"k": {"$toString": "$imports"}}},
            {"$match": {"k": {"$nin": [None, ""]}}},
            {"$group": {"_id": "$k"}},
            {"$count": "c"},
        ]
        ptm_unique_pipeline = [
            {"$project": {"pretrainedModels": {"$ifNull": ["$pretrainedModels", []]}}},
            {"$unwind": "$pretrainedModels"},
            {"$addFields": {"k": {"$toString": "$pretrainedModels"}}},
            {"$match": {"k": {"$nin": [None, ""]}}},
            {"$group": {"_id": "$k"}},
            {"$count": "c"},
        ]
        module_unique_pipeline = [
            {"$addFields": {"module_key": _module_key_expr()}},
            {"$match": {"module_key": {"$nin": [None, ""]}}},
            {"$group": {"_id": "$module_key"}},
            {"$count": "c"},
        ]

        tpl_unique = 0
        r = list(repos_col.aggregate(tpl_unique_pipeline, allowDiskUse=True))
        if r:
            tpl_unique = int(r[0].get("c") or 0)

        ptm_unique = 0
        r = list(repos_col.aggregate(ptm_unique_pipeline, allowDiskUse=True))
        if r:
            ptm_unique = int(r[0].get("c") or 0)

        module_unique = 0
        r = list(modules_col.aggregate(module_unique_pipeline, allowDiskUse=True))
        if r:
            module_unique = int(r[0].get("c") or 0)

        last_updated = None
        try:
            db = get_db()
            doc = db["stats"].find_one({"_id": "global_stats"}, {"last_updated": 1})
            if doc:
                last_updated = doc.get("last_updated")
                if isinstance(last_updated, datetime):
                    if last_updated.tzinfo is None:
                        last_updated = last_updated.replace(tzinfo=timezone.utc)
                    last_updated = (
                        last_updated.replace(microsecond=0)
                        .isoformat()
                        .replace("+00:00", "Z")
                    )
        except Exception:
            last_updated = None

        return jsonify(
            {
                "success": True,
                "summary": {
                    "total_repos": int(total_repos),
                    "unique_tpl": tpl_unique,
                    "unique_ptm": ptm_unique,
                    "unique_module": module_unique,
                    "last_updated": last_updated,
                },
            }
        )
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/analytics/top_tpls")
def api_analytics_top_tpls():
    try:
        limit = _clamp_int(request.args.get("limit", 20), default=20, max_value=100)
        repos_col, _ = get_mongo()

        pipeline = [
            {"$project": {"pid": _project_id_expr(), "imports": {"$ifNull": ["$imports", []]}}},
            {"$unwind": "$imports"},
            {"$addFields": {"k": {"$toString": "$imports"}}},
            {"$match": {"pid": {"$ne": None}, "k": {"$nin": [None, ""]}}},
            {"$group": {"_id": {"k": "$k", "p": "$pid"}}},
            {"$group": {"_id": "$_id.k", "repo_count": {"$sum": 1}}},
            {"$sort": {"repo_count": -1, "_id": 1}},
            {"$limit": limit},
        ]
        items = [{"name": row["_id"], "repo_count": int(row.get("repo_count") or 0)} for row in repos_col.aggregate(pipeline, allowDiskUse=True)]
        return jsonify({"success": True, "items": items})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/analytics/top_ptms")
def api_analytics_top_ptms():
    try:
        limit = _clamp_int(request.args.get("limit", 20), default=20, max_value=100)
        repos_col, _ = get_mongo()

        pipeline = [
            {"$project": {"pid": _project_id_expr(), "pretrainedModels": {"$ifNull": ["$pretrainedModels", []]}}},
            {"$unwind": "$pretrainedModels"},
            {"$addFields": {"k": {"$toString": "$pretrainedModels"}}},
            {"$match": {"pid": {"$ne": None}, "k": {"$nin": [None, ""]}}},
            {"$group": {"_id": {"k": "$k", "p": "$pid"}}},
            {"$group": {"_id": "$_id.k", "repo_count": {"$sum": 1}}},
            {"$sort": {"repo_count": -1, "_id": 1}},
            {"$limit": limit},
        ]
        items = [{"name": row["_id"], "repo_count": int(row.get("repo_count") or 0)} for row in repos_col.aggregate(pipeline, allowDiskUse=True)]
        return jsonify({"success": True, "items": items})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/analytics/top_modules")
def api_analytics_top_modules():
    try:
        limit = _clamp_int(request.args.get("limit", 20), default=20, max_value=100)
        _, modules_col = get_mongo()

        pipeline = [
            {"$addFields": {"module_key": _module_key_expr(), "pid": _project_id_expr()}},
            {"$match": {"pid": {"$ne": None}, "module_key": {"$nin": [None, ""]}}},
            {"$group": {"_id": {"k": "$module_key", "p": "$pid"}, "occ": {"$sum": 1}}},
            {"$group": {"_id": "$_id.k", "repo_count": {"$sum": 1}, "occurrences": {"$sum": "$occ"}}},
            {"$sort": {"repo_count": -1, "occurrences": -1, "_id": 1}},
            {"$limit": limit},
        ]
        items = [
            {
                "name": row["_id"],
                "repo_count": int(row.get("repo_count") or 0),
                "occurrences": int(row.get("occurrences") or 0),
            }
            for row in modules_col.aggregate(pipeline, allowDiskUse=True)
        ]
        return jsonify({"success": True, "items": items})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/analytics/module/detail")
def api_analytics_module_detail():
    """
    Query params:
      - name (module key)
      - limit (top repos, default=20, max=50)
    """
    try:
        name = (request.args.get("name") or "").strip()
        if not name:
            return jsonify({"success": False, "message": "missing query param: name"}), 400

        limit = _clamp_int(request.args.get("limit", 20), default=20, max_value=50)
        repos_col, modules_col = get_mongo()

        pipeline = [
            {"$addFields": {"module_key": _module_key_expr(), "pid": _project_id_expr()}},
            {"$match": {"pid": {"$ne": None}, "module_key": name}},
            {"$group": {"_id": "$pid", "occurrences": {"$sum": 1}}},
            {"$sort": {"occurrences": -1, "_id": 1}},
            {"$limit": limit},
        ]

        per_repo = list(modules_col.aggregate(pipeline, allowDiskUse=True))
        project_ids = [row["_id"] for row in per_repo if row.get("_id") is not None]
        repo_map = {}
        if project_ids:
            for doc in repos_col.find(
                {"$or": [{"projectID": {"$in": project_ids}}, {"projectId": {"$in": project_ids}}]},
                {"projectID": 1, "projectId": 1, "full_name": 1, "stars": 1, "forks": 1, "created_at": 1, "description": 1, "topics": 1},
            ):
                pid = doc.get("projectID", None)
                if pid is None:
                    pid = doc.get("projectId", None)
                if pid is not None:
                    repo_map[pid] = doc

        items = []
        total_occ = 0
        for row in per_repo:
            pid = row["_id"]
            occ = int(row.get("occurrences") or 0)
            total_occ += occ
            r = repo_map.get(pid) or {}
            full_name = r.get("full_name") or ""
            items.append(
                {
                    "projectID": pid,
                    "full_name": full_name,
                    "stars": int(r.get("stars") or 0),
                    "forks": int(r.get("forks") or 0),
                    "created_at": r.get("created_at") or "",
                    "domains": r.get("topics") if isinstance(r.get("topics"), list) else [],
                    "occurrences": occ,
                }
            )

        return jsonify(
            {
                "success": True,
                "module": {"name": name, "total_occurrences": int(total_occ), "repo_count": len(project_ids)},
                "top_repos": items,
            }
        )
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/analytics/component/detail")
def api_analytics_component_detail():
    """
    Generic drilldown for TPL/PTM.
    Query params:
      - type (tpl|ptm)
      - name (component key)
      - limit (default=30, max=50)
    """
    try:
        comp_type = (request.args.get("type") or "").strip().lower()
        name = (request.args.get("name") or "").strip()
        if comp_type not in ("tpl", "ptm"):
            return jsonify({"success": False, "message": "type must be tpl or ptm"}), 400
        if not name:
            return jsonify({"success": False, "message": "missing query param: name"}), 400

        limit = _clamp_int(request.args.get("limit", 30), default=30, max_value=50)
        repos_col, _ = get_mongo()

        field = "imports" if comp_type == "tpl" else "pretrainedModels"
        mongo_filter = {field: name}
        projection = {"projectID": 1, "projectId": 1, "full_name": 1, "stars": 1, "forks": 1, "created_at": 1, "description": 1, "topics": 1}

        cursor = repos_col.find(mongo_filter, projection).sort([("stars", DESCENDING), ("full_name", ASCENDING)]).limit(limit)

        items = []
        for doc in cursor:
            pid = doc.get("projectID", None)
            if pid is None:
                pid = doc.get("projectId", None)
            items.append(
                {
                    "projectID": pid,
                    "full_name": doc.get("full_name") or "",
                    "stars": int(doc.get("stars") or 0),
                    "forks": int(doc.get("forks") or 0),
                    "created_at": doc.get("created_at") or "",
                    "domains": doc.get("topics") if isinstance(doc.get("topics"), list) else [],
                }
            )

        total = repos_col.count_documents(mongo_filter)
        return jsonify(
            {
                "success": True,
                "component": {"type": comp_type, "name": name, "repo_count": int(total)},
                "top_repos": items,
            }
        )
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500



# 启动应用
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
