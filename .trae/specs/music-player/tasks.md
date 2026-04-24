# 音乐在线播放平台 - The Implementation Plan (Decomposed and Prioritized Task List)

## [x] Task 1: 项目初始化与基础架构搭建
- **Priority**: P0
- **Depends On**: None
- **Description**: 
  - 使用UV初始化Python项目，创建项目结构
  - 安装FastAPI、Jinja2、SQLite相关依赖
  - 创建配置管理模块（环境变量、API密钥管理）
  - 搭建FastAPI应用骨架，包含路由、静态文件、模板配置
  - 创建项目目录结构：app/ (core, models, routers, services, templates, static)
- **Acceptance Criteria Addressed**: AC-8
- **Test Requirements**:
  - `programmatic` TR-1.1: 项目能够通过`uv run`启动，访问首页返回200状态码
  - `programmatic` TR-1.2: 配置文件正确加载API密钥（测试用假密钥即可验证加载机制）
  - `human-judgement` TR-1.3: 项目结构清晰，符合FastAPI最佳实践
- **Notes**: 使用Python 3.11+，确保所有依赖通过UV管理

## [x] Task 2: 数据库模型设计与创建
- **Priority**: P0
- **Depends On**: Task 1
- **Description**: 
  - 设计SQLite数据库模型（使用SQLAlchemy Core或ORM）
  - 核心表：songs, artists, albums, genres, playlists, playlist_songs, graph_edges
  - songs表字段：id, external_id, source, name, artist_id, album_id, duration, audio_url, cover_url, metadata_json, created_at
  - artists表字段：id, external_id, source, name, bio, image_url, metadata_json
  - albums表字段：id, external_id, source, name, artist_id, release_date, cover_url, metadata_json
  - genres表字段：id, name, description
  - playlists表字段：id, name, cover_url, created_at, updated_at
  - playlist_songs表字段：playlist_id, song_id, order_index, added_at
  - graph_edges表（知识图谱）：id, from_type, from_id, to_type, to_id, relation_type, weight, created_at
  - 创建数据库初始化脚本和迁移管理
- **Acceptance Criteria Addressed**: AC-4, AC-6
- **Test Requirements**:
  - `programmatic` TR-2.1: 数据库初始化脚本能够成功创建所有表和索引
  - `programmatic` TR-2.2: 能够向各表插入测试数据并正确查询
  - `programmatic` TR-2.3: 外键约束正确生效（如删除歌单时级联删除playlist_songs记录或报错）
- **Notes**: 使用SQLAlchemy 2.0风格，考虑使用Alembic进行迁移，但初期可简化为初始化脚本

## [x] Task 3: Jamendo数据源集成服务
- **Priority**: P0
- **Depends On**: Task 2
- **Description**: 
  - 实现Jamendo API客户端封装
  - 支持搜索：按关键词搜索歌曲、艺术家、专辑、按风格搜索
  - 支持获取详情：获取歌曲详情、艺术家详情、专辑详情
  - 支持获取音频流URL（preview或完整流，根据API能力）
  - 实现数据缓存机制：将获取的元数据存入本地数据库
  - 实现速率限制和错误重试机制
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - `programmatic` TR-3.1: 搜索API调用成功返回结果，数据格式正确
  - `programmatic` TR-3.2: 搜索结果能够正确缓存到本地数据库
  - `programmatic` TR-3.3: 重复搜索相同关键词优先返回缓存数据
  - `programmatic` TR-3.4: API调用失败时有正确的错误处理（不崩溃）
- **Notes**: Jamendo需要API Key，通过环境变量配置，实现mock模式便于开发测试

## [ ] Task 4: MusicBrainz数据源集成服务
- **Priority**: P1
- **Depends On**: Task 3
- **Description**: 
  - 实现MusicBrainz API客户端封装
  - 支持搜索和获取详细元数据
  - 实现数据标准化，将MusicBrainz数据映射到统一的内部模型
  - 可选：实现多源数据融合（优先Jamendo有音频的，用MusicBrainz补充元数据）
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - `programmatic` TR-4.1: MusicBrainz API调用成功，返回预期格式数据
  - `programmatic` TR-4.2: 数据能够正确映射到内部模型并存入数据库
- **Notes**: MusicBrainz有严格的速率限制（1 req/s），必须实现请求限流和User-Agent标识

## [x] Task 5: 搜索API与后台路由
- **Priority**: P0
- **Depends On**: Task 3
- **Description**: 
  - 实现搜索API端点：GET /api/search?q={keyword}&type={songs|artists|albums|all}
  - 实现搜索结果聚合：优先查本地缓存，无结果或结果过少时调用外部API
  - 实现搜索结果分页
  - 创建搜索页面模板
- **Acceptance Criteria Addressed**: AC-1
- **Test Requirements**:
  - `programmatic` TR-5.1: 搜索API返回正确格式的JSON响应
  - `programmatic` TR-5.2: 搜索API支持按类型过滤
  - `programmatic` TR-5.3: 分页参数生效（page, limit）
  - `human-judgement` TR-5.4: 搜索页面UI正确展示结果列表
- **Notes**: 搜索类型包括：songs, artists, albums, genres

## [x] Task 6: 流媒体代理服务
- **Priority**: P0
- **Depends On**: Task 2
- **Description**: 
  - 实现音频流代理端点：GET /api/stream/{song_id}
  - 支持HTTP Range Requests（实现进度拖动）
  - 从数据库获取song的audio_url，代理请求外部音频源
  - 添加合适的CORS头和缓存控制头
  - 实现错误处理（如源URL失效时返回404）
- **Acceptance Criteria Addressed**: AC-2
- **Test Requirements**:
  - `programmatic` TR-6.1: 流端点能够成功返回音频数据
  - `programmatic` TR-6.2: Range请求能够正确返回部分内容（206状态码）
  - `programmatic` TR-6.3: 无效的song_id返回404
  - `programmatic` TR-6.4: CORS头正确设置（允许前端访问）
- **Notes**: 使用httpx或aiohttp进行异步请求，避免阻塞FastAPI事件循环

## [x] Task 7: 播放控制API与播放器前端
- **Priority**: P0
- **Depends On**: Task 6
- **Description**: 
  - 实现歌曲详情API：GET /api/songs/{song_id}
  - 创建基础播放器UI（HTML/CSS/JS）
  - 实现Audio元素控制：播放/暂停、上一曲/下一曲（暂时占位，需歌单配合）
  - 实现进度条：显示当前时间/总时长，支持拖动跳转
  - 实现音量控制滑块和静音按钮
  - 显示当前播放歌曲信息：歌名、艺术家、封面
- **Acceptance Criteria Addressed**: AC-2
- **Test Requirements**:
  - `programmatic` TR-7.1: 歌曲详情API返回完整的歌曲信息
  - `programmatic` TR-7.2: 播放器页面成功加载，Audio元素能够绑定流URL
  - `human-judgement` TR-7.3: 播放控制按钮工作正常，进度条可拖动
  - `human-judgement` TR-7.4: 音量控制和静音功能正常
- **Notes**: 使用原生HTML5 Audio API，无需引入额外播放器库，保持轻量

## [x] Task 8: 歌单管理API
- **Priority**: P0
- **Depends On**: Task 2
- **Description**: 
  - 歌单CRUD API：
    - GET /api/playlists - 获取所有歌单列表
    - GET /api/playlists/{id} - 获取歌单详情（含歌曲列表）
    - POST /api/playlists - 创建歌单 {name}
    - PUT /api/playlists/{id} - 更新歌单信息 {name}
    - DELETE /api/playlists/{id} - 删除歌单
  - 歌单歌曲管理API：
    - POST /api/playlists/{id}/songs - 添加歌曲 {song_id}
    - DELETE /api/playlists/{id}/songs/{song_id} - 移除歌曲
    - PUT /api/playlists/{id}/reorder - 调整歌曲顺序 {order: [song_id_1, song_id_2...]}
- **Acceptance Criteria Addressed**: AC-4
- **Test Requirements**:
  - `programmatic` TR-8.1: 创建歌单成功，数据库正确插入记录
  - `programmatic` TR-8.2: 向歌单添加歌曲成功，playlist_songs表正确记录
  - `programmatic` TR-8.3: 从歌单移除歌曲成功
  - `programmatic` TR-8.4: 删除歌单成功，级联删除关联记录
  - `programmatic` TR-8.5: 歌单歌曲顺序调整正确生效
- **Notes**: 实现默认"喜欢的音乐"歌单或让用户从空开始

## [x] Task 9: 歌单管理前端界面
- **Priority**: P0
- **Depends On**: Task 8
- **Description**: 
  - 创建歌单列表页面
  - 创建歌单详情页面（展示歌曲列表）
  - 在搜索结果和歌曲详情页面添加"添加到歌单"功能
  - 在歌单详情页面支持移除歌曲和调整顺序（拖放或上下按钮）
  - 支持歌单重命名和删除（带确认提示）
- **Acceptance Criteria Addressed**: AC-4
- **Test Requirements**:
  - `human-judgement` TR-9.1: 歌单列表正确显示所有歌单
  - `human-judgement` TR-9.2: 歌单详情正确显示歌曲列表
  - `human-judgement` TR-9.3: "添加到歌单"功能工作正常
  - `human-judgement` TR-9.4: 歌曲移除和歌单删除功能正常
- **Notes**: 添加成功/失败的用户反馈提示（toast消息）

## [x] Task 10: 歌单播放与播放模式
- **Priority**: P0
- **Depends On**: Task 7, Task 9
- **Description**: 
  - 支持从歌单播放：点击歌单中的歌曲开始播放
  - 实现播放队列概念：当前播放列表
  - 实现播放模式切换：顺序播放、随机播放、单曲循环
  - 实现上一曲/下一曲功能（根据当前模式行为不同）
  - 播放器显示当前播放队列信息
- **Acceptance Criteria Addressed**: AC-2, AC-5
- **Test Requirements**:
  - `programmatic` TR-10.1: 顺序播放模式下，歌曲播放完毕自动播放下一首
  - `programmatic` TR-10.2: 单曲循环模式下，歌曲播放完毕重新播放同一首
  - `programmatic` TR-10.3: 随机播放模式下，下一曲逻辑是随机的（测试多次确认不是固定顺序）
  - `human-judgement` TR-10.4: 上一曲/下一曲按钮工作正常，符合当前播放模式
- **Notes**: 播放队列状态可以存在前端localStorage或后端session，优先前端实现简化后端

## [ ] Task 11: 知识图谱构建服务
- **Priority**: P1
- **Depends On**: Task 2
- **Description**: 
  - 实现图谱构建逻辑：从已有的songs, artists, albums, genres数据构建graph_edges
  - 定义关系类型：
    - `artist_sings` (artist -> song)
    - `album_contains` (album -> song)
    - `song_has_genre` (song -> genre)
    - `artist_collaborates` (artist -> artist, 基于共同演唱歌曲)
  - 实现图谱构建API/后台任务：POST /api/graph/build（扫描现有数据构建边）
  - 实现实时图谱更新：添加新歌时自动添加相关边
- **Acceptance Criteria Addressed**: AC-6
- **Test Requirements**:
  - `programmatic` TR-11.1: 构建图谱后，graph_edges表中正确存在artist_sings类型边
  - `programmatic` TR-11.2: 构建图谱后，正确存在album_contains和song_has_genre类型边
  - `programmatic` TR-11.3: 添加新歌后，相关边自动创建（可查询验证）
- **Notes**: weight字段可用于后续推荐排序（如按流行度、关联强度）

## [ ] Task 12: 图谱查询API
- **Priority**: P1
- **Depends On**: Task 11
- **Description**: 
  - 实现图谱查询端点：
    - GET /api/graph/artist/{id}/songs - 获取艺术家的所有歌曲
    - GET /api/graph/song/{id}/similar - 获取相似歌曲（同风格、同专辑）
    - GET /api/graph/artist/{id}/collaborators - 获取合作过的艺术家
    - GET /api/graph/genre/{name}/songs - 获取某风格的歌曲
  - 实现灵活的图谱遍历查询（可扩展）
- **Acceptance Criteria Addressed**: AC-6
- **Test Requirements**:
  - `programmatic` TR-12.1: 查询艺术家歌曲返回正确列表
  - `programmatic` TR-12.2: 查询相似歌曲返回同风格/同专辑的歌曲
  - `programmatic` TR-12.3: 查询合作艺术家返回有共同歌曲的艺术家
- **Notes**: SQL查询使用JOIN graph_edges实现，确保查询效率

## [ ] Task 13: 推荐系统算法实现
- **Priority**: P1
- **Depends On**: Task 12
- **Description**: 
  - 实现基于图谱的推荐算法：
    1. **同风格推荐**：给歌曲A，推荐同genre且不同artist的歌曲
    2. **同艺术家推荐**：给歌曲A，推荐同artist的其他歌曲
    3. **路径推荐**：给歌曲A，推荐"歌曲A的artist合作过的artist的热门歌曲"（2跳路径）
  - 实现推荐评分/排序机制（综合考虑多种信号）
  - 实现播放历史记录：记录用户播放过的歌曲（用于历史基推荐）
- **Acceptance Criteria Addressed**: AC-7
- **Test Requirements**:
  - `programmatic` TR-13.1: 同风格推荐返回与输入歌曲相同genre的其他歌曲
  - `programmatic` TR-13.2: 同艺术家推荐返回同一艺术家的其他歌曲
  - `programmatic` TR-13.3: 播放历史正确记录和查询
  - `programmatic` TR-13.4: 推荐结果包含推荐理由说明字段（如"同风格推荐"、"来自你喜欢的艺术家"）
- **Notes**: 推荐理由字段很重要，让推荐可解释

## [ ] Task 14: 推荐API与前端展示
- **Priority**: P1
- **Depends On**: Task 13
- **Description**: 
  - 实现推荐API端点：
    - GET /api/recommendations/for-song/{song_id} - 基于当前歌曲推荐
    - GET /api/recommendations/for-you - 基于播放历史推荐
  - 创建推荐展示组件
  - 在播放器页面显示"相似歌曲"推荐
  - 在首页显示"为你推荐"板块
  - 支持一键将推荐歌曲添加到歌单
- **Acceptance Criteria Addressed**: AC-7
- **Test Requirements**:
  - `programmatic` TR-14.1: 推荐API返回格式正确，包含recommendation_reason字段
  - `human-judgement` TR-14.2: 推荐列表在UI上正确展示
  - `human-judgement` TR-14.3: 从推荐列表添加歌曲到歌单功能正常
- **Notes**: 推荐结果去重（不要推荐正在播放的那首）

## [ ] Task 15: 音频可视化 - 基础架构
- **Priority**: P1
- **Depends On**: Task 7
- **Description**: 
  - 使用Web Audio API创建AudioContext
  - 连接Audio元素到AnalyserNode
  - 实现requestAnimationFrame循环获取频率数据
  - 创建可视化Canvas容器
  - 实现可视化模式切换UI（下拉或按钮组）
- **Acceptance Criteria Addressed**: AC-3
- **Test Requirements**:
  - `programmatic` TR-15.1: AudioContext成功创建，AnalyserNode正确连接
  - `human-judgement` TR-15.2: 模式切换UI存在且可点击
- **Notes**: 注意AudioContext需要用户交互（如点击播放）才能解锁，处理好这个限制

## [ ] Task 16: 音频可视化 - 多种模式实现
- **Priority**: P1
- **Depends On**: Task 15
- **Description**: 
  - **模式1: 频谱柱状图 (Bars)**
    - 从AnalyserNode获取frequencyBinCount数据
    - 在Canvas上绘制动态柱状图，高度随频率能量变化
    - 添加渐变颜色效果
  - **模式2: 波形图 (Wave)**
    - 获取timeDomainData
    - 绘制连续的波形曲线
  - **模式3: 动态粒子效果 (Particles)**
    - 创建粒子系统，粒子的运动/大小/颜色响应音频能量
    - 低频时粒子运动慢，高频时粒子活跃/颜色变化
- **Acceptance Criteria Addressed**: AC-3
- **Test Requirements**:
  - `human-judgement` TR-16.1: 频谱柱状图模式正常显示，随音乐节奏变化
  - `human-judgement` TR-16.2: 波形图模式正常显示
  - `human-judgement` TR-16.3: 粒子效果模式正常显示，动态效果流畅
  - `human-judgement` TR-16.4: 三种模式之间可切换，切换时渲染干净无残留
- **Notes**: 保持代码模块化，每种可视化模式为独立的渲染函数

## [ ] Task 17: 主页与整体UI整合
- **Priority**: P2
- **Depends On**: Task 5, Task 7, Task 9, Task 14, Task 16
- **Description**: 
  - 创建统一的导航栏（搜索、歌单、推荐入口）
  - 创建主页布局：
    - 顶部：搜索栏
    - 中部：推荐板块、热门歌单、浏览入口
    - 底部：固定播放器栏（迷你模式，点击展开）
  - 实现响应式布局（适配桌面和移动端屏幕）
  - 统一的CSS样式和视觉风格
- **Acceptance Criteria Addressed**: AC-8
- **Test Requirements**:
  - `human-judgement` TR-17.1: 导航栏在所有页面一致，各入口可点击跳转
  - `human-judgement` TR-17.2: 固定播放器栏在底部，播放状态跨页面保持
  - `human-judgement` TR-17.3: 页面布局在不同窗口大小下合理（响应式）
- **Notes**: 底部播放器栏使用position: fixed，是现代音乐APP的标准模式

## [ ] Task 18: 项目配置、文档与启动脚本
- **Priority**: P2
- **Depends On**: Task 1
- **Description**: 
  - 完善.env.example模板文件（说明需要配置哪些环境变量，如JAMENDO_CLIENT_ID）
  - 创建README.md（项目介绍、安装步骤、配置说明、运行方式）
  - 创建启动脚本：uv run uvicorn app.main:app --reload
  - 确保所有配置项可通过环境变量覆盖
  - 实现开发模式和生产模式区分
- **Acceptance Criteria Addressed**: AC-8
- **Test Requirements**:
  - `programmatic` TR-18.1: 通过uv run能够一键启动项目
  - `human-judgement` TR-18.2: .env.example文件清晰说明所有必需配置
  - `human-judgement` TR-18.3: README文档完整，新用户能够按照步骤启动项目
- **Notes**: README中说明如何申请Jamendo API Key

## [ ] Task 19: 端到端集成测试与修复
- **Priority**: P0
- **Depends On**: Task 18
- **Description**: 
  - 端到端测试主流程：
    1. 搜索歌曲
    2. 播放歌曲
    3. 查看可视化效果并切换模式
    4. 创建歌单并添加歌曲
    5. 从歌单播放，测试各播放模式
    6. 查看推荐并添加到歌单
  - 发现并修复流程中的Bug
  - 优化用户体验细节（加载状态、错误提示、空状态）
- **Acceptance Criteria Addressed**: AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8
- **Test Requirements**:
  - `human-judgement` TR-19.1: 主流程端到端走通无阻塞性Bug
  - `human-judgement` TR-19.2: 所有页面有合适的加载状态和错误提示
  - `human-judgement` TR-19.3: 空状态（无歌单、无搜索结果）有友好提示
- **Notes**: 这是一个综合性验证任务，确保所有模块整合良好
