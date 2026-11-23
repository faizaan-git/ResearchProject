from pathlib import PurePosixPath

from app.project_ingestion.code_analyzer import analyze_python_project
from fastapi import UploadFile, File
from app.project_ingestion.zip_handler import extract_project_zip
from app.agents.web_research import web_research_agent
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.agents.research_planner import research_planner
from app.project_ingestion.project_scanner import scan_project
from app.project_ingestion.github_handler import ingest_github_repository
from app.project_ingestion.project_history import (
    delete_project_analysis,
    get_project_analysis,
    list_recent_projects,
    save_project_analysis,
)

app = FastAPI(
    title="ProjectResearch",
    description="Autonomous multi-agent web research and project source analysis platform",
    version="0.2.0"
)


# Allow the React frontend to communicate with the backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ResearchPlanRequest(BaseModel):
    topic: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="The topic to research"
    )
class WebResearchRequest(BaseModel):
    queries: list[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="List of web research search queries"
    )


class ResearchRunRequest(BaseModel):
    topic: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="The topic for complete research"
    )

class GitHubProjectRequest(BaseModel):
    repository_url: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Public GitHub repository URL"
    )


@app.get("/")
async def root():
    return {
        "message": "ProjectResearch Backend is running!",
        "project": "ProjectResearch",
        "version": "0.2.0"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "application": "ProjectResearch",
        "backend": "FastAPI"
    }


@app.get("/api/v1/system/info")
async def system_info():
    return {
        "project": "ProjectResearch",
        "description": "Autonomous AI-powered web research and project source analysis",
        "initial_agents": [
            "Research Planner Agent",
            "Web Research Agent",
            "Research Analysis Agent"
        ],
        "status": "initializing"
    }


@app.post("/api/v1/research/plan")
async def create_research_plan(request: ResearchPlanRequest):
    try:
        plan = research_planner.create_plan(request.topic)

        return {
            "success": True,
            "message": "Research plan created successfully",
            "data": plan
        }

    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error)
        )

@app.post("/api/v1/research/search")
async def search_research_sources(request: WebResearchRequest):
    try:
        results = web_research_agent.search_web(
            queries=request.queries,
            max_results=5
        )

        return {
            "success": True,
            "message": "Web research completed",
            "data": results
        }

    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Web research failed: {str(error)}"
        )


@app.post("/api/v1/research/run")
def run_complete_research(request: ResearchRunRequest):
    try:
        # Step 1: Generate research plan
        plan = research_planner.create_plan(request.topic)

        # Step 2: Extract search queries
        queries = plan["suggested_search_queries"]

        # Step 3: Search the web
        research_results = web_research_agent.search_web(
            queries=queries,
            max_results=3
        )

        # Step 4: Return combined results
        return {
            "success": True,
            "message": "Complete research workflow executed",
            "data": {
                "research_plan": plan,
                "web_research": research_results
            }
        }

    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error)
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Research workflow failed: {str(error)}"
        )


@app.post("/api/v1/projects/upload")
async def upload_project(file: UploadFile = File(...)):
    try:
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="Please select a ZIP file."
            )

        if not file.filename.lower().endswith(".zip"):
            raise HTTPException(
                status_code=400,
                detail="Only ZIP files are supported."
            )

        zip_bytes = await file.read(100 * 1024 * 1024 + 1)

        # Step 1: Extract uploaded project
        upload_result = extract_project_zip(
            zip_bytes=zip_bytes,
            original_filename=file.filename
        )

        project_directory = upload_result["project_directory"]

        # Step 2: Detect technologies and project files
        try:
            project_analysis = scan_project(project_directory)
            scan_status = "completed"

        except ValueError as error:
            project_analysis = {"error": str(error)}
            scan_status = "incomplete"

        # Step 3: Analyze Python source code
        try:
            code_analysis = analyze_python_project(
                project_directory
            )
            code_analysis_status = "completed"

        except ValueError as error:
            code_analysis = {"error": str(error)}
            code_analysis_status = "incomplete"

        # Step 4: Save and return complete analysis
        analysis_data = {
            "source_type": "zip_upload",
            "repository_name": (
                PurePosixPath(file.filename.replace("\\", "/")).stem
                or "Uploaded project"
            ),
            "repository_url": "",
            "upload": {
                **upload_result,
                "filename": file.filename,
            },
            "scan_status": scan_status,
            "project_analysis": project_analysis,
            "code_analysis_status": code_analysis_status,
            "code_analysis": code_analysis,
        }
        saved_project = save_project_analysis(analysis_data)
        analysis_data["project_id"] = saved_project["id"]

        return {
            "success": True,
            "message": "Project uploaded and analyzed successfully",
            "data": analysis_data,
        }

    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error)
        )

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Project upload failed: {str(error)}"
        )

    finally:
        await file.close()



@app.post("/api/v1/projects/github")
def ingest_github_project(request: GitHubProjectRequest):
    try:
        # Step 1: Download and extract GitHub repository
        github_result = ingest_github_repository(
            request.repository_url
        )

        upload_result = github_result["upload"]
        project_directory = upload_result["project_directory"]

        # Step 2: Detect technologies and project files
        try:
            project_analysis = scan_project(project_directory)
            scan_status = "completed"

        except ValueError as error:
            project_analysis = {"error": str(error)}
            scan_status = "incomplete"

        # Step 3: Analyze Python source code
        try:
            code_analysis = analyze_python_project(
                project_directory
            )
            code_analysis_status = "completed"

        except ValueError as error:
            code_analysis = {"error": str(error)}
            code_analysis_status = "incomplete"

        # Step 4: Save and return complete project analysis
        analysis_data = {
            "source_type": github_result["source_type"],
            "repository_url": github_result["repository_url"],
            "repository_owner": github_result["repository_owner"],
            "repository_name": github_result["repository_name"],
            "upload": upload_result,
            "scan_status": scan_status,
            "project_analysis": project_analysis,
            "code_analysis_status": code_analysis_status,
            "code_analysis": code_analysis,
        }
        saved_project = save_project_analysis(analysis_data)
        analysis_data["project_id"] = saved_project["id"]

        return {
            "success": True,
            "message": "GitHub repository downloaded and analyzed successfully",
            "data": analysis_data,
        }

    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error)
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"GitHub project ingestion failed: {str(error)}"
        )


@app.get("/api/v1/projects/recent")
def get_recent_projects(limit: int = Query(default=10, ge=1, le=10)):
    return {
        "success": True,
        "data": list_recent_projects(limit),
    }


@app.get("/api/v1/projects/recent/{project_id}")
def get_saved_project(project_id: str):
    analysis = get_project_analysis(project_id)

    if analysis is None:
        raise HTTPException(
            status_code=404,
            detail="The requested project analysis was not found."
        )

    return {
        "success": True,
        "data": analysis,
    }


@app.delete("/api/v1/projects/recent/{project_id}")
def delete_saved_project(project_id: str):
    if not delete_project_analysis(project_id):
        raise HTTPException(
            status_code=404,
            detail="The requested project analysis was not found."
        )

    return {
        "success": True,
        "message": "Project analysis deleted successfully.",
        "data": {"id": project_id},
    }
