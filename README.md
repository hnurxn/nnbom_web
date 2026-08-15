# NNBOM Visualization Platform

NNBOM Visualization Platform 是一个面向神经网络物料清单（Neural Network Bill of Materials, NNBOM）的可视化分析平台，用于统一展示和查询神经网络项目、代码模块及相关组件信息，帮助研究人员理解神经网络软件的组成、依赖与复用关系。

## 主要功能

- 展示神经网络项目的基本信息与统计结果
- 查询项目包含的神经网络模块及其代码位置
- 展示项目的领域、依赖包和预训练模型等组件信息
- 基于 `projectID` 关联项目元数据与模块数据
- 为 NNBOM 的构建、分析与演化研究提供可视化支持

## 系统架构

- **Frontend:** Vue.js、HTML、CSS、JavaScript、Axios
- **Backend:** Python、Flask
- **Database:** MongoDB
- **Deployment:** Docker（用于快速部署 MongoDB）

前端通过 Axios 调用 Flask 提供的 REST API；后端从 MongoDB 中读取 NNBOM 数据并返回查询与统计结果。

## 数据模型

平台主要包含两类数据：

- **Repos:** 保存项目级元数据，如项目名称、版本、Star、Fork、领域、依赖包和预训练模型等。
- **Modules:** 保存神经网络模块信息，如模块名称、文件路径、代码行范围和模块哈希等。

两类数据通过 `projectID` 建立关联。

## 快速开始

### 1. 获取代码

```bash
git clone <repository-url>
cd <repository-directory>
```

前端和后端代码均包含在当前项目中。请将上述地址和目录名称替换为实际的 GitHub 仓库信息。

### 2. 启动 MongoDB

确保本地已安装 Docker，然后执行：

```bash
docker run --name nnbom-mongo \
  -d \
  -p 27017:27017 \
  -v "$(pwd)/mongo_data:/data/db" \
  mongo:latest
```

如已创建容器，可使用以下命令重新启动：

```bash
docker start nnbom-mongo
```

### 3. 启动后端

在项目根目录下进入后端目录并安装依赖：

```bash
cd backend
pip install -r requirements.txt
python app.py
```

后端默认监听地址以 `app.py` 中的配置或终端输出为准，通常为 `http://127.0.0.1:5000`。

### 4. 启动前端

另开一个终端，在项目根目录下进入前端目录：

```bash
cd frontend
python -m http.server 8000
```

在浏览器中访问：

```text
http://127.0.0.1:8000
```

如果前端无法访问后端，请检查前端 API 地址、后端端口以及跨域配置是否一致。

## 项目说明

本平台服务于 NNBOM 的可视化展示与分析。NNBOM 通过对神经网络软件中的项目、代码模块、依赖包和预训练模型等组件进行统一描述，为神经网络软件的成分识别、复用分析和供应链治理提供数据基础。

## Citation

如果本项目对你的研究有所帮助，欢迎引用与 NNBOM 相关的论文或项目成果。具体引用信息将在后续补充。

## Contact

如有问题或建议，欢迎通过 GitHub Issues 反馈。
