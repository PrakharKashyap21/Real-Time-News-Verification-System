import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8008";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 60000,
});

export const predictNews = async (title, text) => {
  try {
    const response = await apiClient.post("/predict", {
      title: title || "",
      text: text || "",
    });
    return response.data;
  } catch (error) {
    if (error.response) {
      if (error.response.status === 422) {
        const detail = error.response.data?.detail;
        if (typeof detail === "string") {
          throw new Error(detail);
        } else if (Array.isArray(detail) && detail.length > 0) {
          throw new Error(detail[0].msg || "Validation error: Please enter valid headline or text.");
        }
        throw new Error("Validation error: Please enter a headline or article text.");
      }
      throw new Error(error.response.data?.detail || "Unable to process prediction request. Please try again later.");
    } else if (error.code === "ECONNABORTED" || error.message?.includes("timeout")) {
      throw new Error("Prediction request timed out. Please try again.");
    } else if (error.request) {
      throw new Error("Unable to connect to the backend server. Please check if the API server is running on " + API_BASE_URL + ".");
    } else {
      throw new Error("An unexpected error occurred while making the request.");
    }
  }
};

export const verifyNewsV2 = async (title, text) => {
  try {
    const response = await apiClient.post("/v2/verify", {
      title: title || "",
      text: text || "",
    });
    return response.data;
  } catch (error) {
    if (error.response) {
      if (error.response.status === 422) {
        const detail = error.response.data?.detail;
        if (typeof detail === "string") {
          throw new Error(detail);
        } else if (Array.isArray(detail) && detail.length > 0) {
          throw new Error(detail[0].msg || "Validation error: Please enter valid title or text.");
        }
        throw new Error("Validation error: At least a title or text of sufficient length is required for verification.");
      }
      throw new Error(error.response.data?.detail || "Unable to complete real-time news verification. Please try again.");
    } else if (error.code === "ECONNABORTED" || error.message?.includes("timeout")) {
      throw new Error("Verification request timed out. External fact-checking and news retrieval took longer than 30 seconds. Please try again.");
    } else if (error.request) {
      throw new Error("Unable to connect to the backend verification server. Please check if the API server is running on " + API_BASE_URL + ".");
    } else {
      throw new Error("An unexpected error occurred during verification.");
    }
  }
};

export const extractArticleFromUrl = async (url) => {
  try {
    const response = await apiClient.post("/v2/extract-url", { url });
    return response.data;
  } catch (error) {
    if (error.response?.data?.detail) {
      throw new Error(error.response.data.detail);
    }
    throw new Error(error.message || "Failed to extract content from the given URL.");
  }
};

export const auditDocumentText = async (title, content) => {
  try {
    const response = await apiClient.post("/v2/audit-document", {
      title: title || "",
      content: content || "",
    });
    return response.data;
  } catch (error) {
    if (error.response?.data?.detail) {
      throw new Error(error.response.data.detail);
    }
    throw new Error(error.message || "Failed to audit document content.");
  }
};

export const auditUploadedFile = async (file) => {
  try {
    const formData = new FormData();
    formData.append("file", file);
    const response = await apiClient.post("/v2/audit-file", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
      timeout: 90000,
    });
    return response.data;
  } catch (error) {
    if (error.response?.data?.detail) {
      throw new Error(error.response.data.detail);
    }
    throw new Error(error.message || "Failed to audit uploaded file.");
  }
};

export const getAnalyticsData = async (domain = "") => {
  try {
    const params = domain ? { domain } : {};
    const response = await apiClient.get("/v2/analytics", { params });
    return response.data;
  } catch (error) {
    if (error.response?.data?.detail) {
      throw new Error(error.response.data.detail);
    }
    throw new Error(error.message || "Failed to fetch analytics intelligence data.");
  }
};

export const getRadarFeed = async (category = "") => {
  try {
    const params = category && category !== "All" ? { category } : {};
    const response = await apiClient.get("/v2/radar", { params });
    return response.data;
  } catch (error) {
    if (error.response?.data?.detail) {
      throw new Error(error.response.data.detail);
    }
    throw new Error(error.message || "Failed to fetch live radar trending feed.");
  }
};


