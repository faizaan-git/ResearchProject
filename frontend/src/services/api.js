
import axios from "axios";

const API = axios.create({
  baseURL: "http://127.0.0.1:8000",
  timeout: 30000,
});

export const ingestGithubRepository = async (repositoryUrl) => {
  const response = await API.post(
    "/api/v1/projects/github",
    {
      repository_url: repositoryUrl,
    },
    {
      timeout: 180000,
    }
  );

  return response.data;
};

export const analyzeProjectArchive = async (file) => {
  const formData = new FormData();
  formData.append("file", file);

  const response = await API.post("/api/v1/projects/upload", formData, {
    timeout: 180000,
  });

  return response.data;
};

export const getRecentProjects = async (limit = 10) => {
  const response = await API.get("/api/v1/projects/recent", {
    params: { limit },
  });

  return response.data;
};

export const getRecentProjectAnalysis = async (projectId) => {
  const response = await API.get(
    `/api/v1/projects/recent/${encodeURIComponent(projectId)}`,
  );

  return response.data;
};

export const deleteRecentProjectAnalysis = async (projectId) => {
  const response = await API.delete(
    `/api/v1/projects/recent/${encodeURIComponent(projectId)}`,
  );

  return response.data;
};
