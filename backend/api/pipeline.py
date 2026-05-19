"""流水线执行 API"""
from fastapi import APIRouter, BackgroundTasks, HTTPException
from backend.schemas.pipeline import (
    PipelineRunRequest, PipelineRunResponse, TaskSummary
)
from backend.services.pipeline_service import pipeline_service, tasks
from backend.services.progress_manager import progress_manager

router = APIRouter(prefix="/api/pipeline", tags=["流水线"])


@router.post("/run", response_model=PipelineRunResponse)
async def run_pipeline(req: PipelineRunRequest, bg: BackgroundTasks):
    """启动流水线任务"""
    if not req.enterprise_names:
        raise HTTPException(400, "企业名称列表不能为空")

    task_id = pipeline_service.create_task(
        enterprise_names=req.enterprise_names,
        output_config=req.output_config.model_dump(),
    )

    bg.add_task(pipeline_service.run_task, task_id)

    return PipelineRunResponse(
        task_id=task_id,
        enterprise_count=len(req.enterprise_names),
        status="queued",
    )


@router.get("/tasks")
async def list_tasks():
    """获取任务列表"""
    return [
        {
            "task_id": t.task_id,
            "enterprise_count": len(t.enterprise_names),
            "status": t.status,
            "completed_count": t.completed_count,
            "failed_count": t.failed_count,
            "created_at": t.created_at,
        }
        for t in tasks.values()
    ]


@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """获取任务详情"""
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(404, f"任务 {task_id} 不存在")
    return {
        "task_id": task.task_id,
        "enterprise_names": task.enterprise_names,
        "status": task.status,
        "completed_count": task.completed_count,
        "failed_count": task.failed_count,
        "output_config": task.output_config,
        "results": task.results,
        "created_at": task.created_at,
    }


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    """取消任务（标记状态，实际停止依赖 asyncio task 取消）"""
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(404, f"任务 {task_id} 不存在")
    task.status = "cancelled"
    progress_manager.clear(task_id)
    return {"message": f"任务 {task_id} 已取消"}


@router.get("/result/{task_id}/{enterprise_name}")
async def get_result(task_id: str, enterprise_name: str):
    """获取单企业执行结果"""
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(404, f"任务 {task_id} 不存在")
    for r in task.results:
        sd = r.get("structured_data", {})
        if sd.get("enterprise_name") == enterprise_name:
            return r
    raise HTTPException(404, f"未找到 {enterprise_name} 的结果")
