const API_BASE = (import.meta.env.VITE_SSK_API_BASE || "").replace(/\/$/, "");
export const AUTH_EXPIRED_EVENT = "ssk-law:auth-expired";

function shouldNotifyAuthExpired(path, method) {
  if (["GET", "HEAD", "OPTIONS", "TRACE"].includes(method)) return false;
  if (path.startsWith("/api/auth/login")) return false;
  if (path.startsWith("/api/auth/csrf")) return false;
  return true;
}

function getCookie(name) {
  const prefix = `${encodeURIComponent(name)}=`;
  const cookie = document.cookie
    .split(";")
    .map((value) => value.trim())
    .find((value) => value.startsWith(prefix));
  return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : "";
}

async function request(path, options = {}) {
  const { suppressAuthExpired = false, ...fetchOptions } = options;
  const method = String(options.method || "GET").toUpperCase();
  const headers = new Headers(options.headers || {});

  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (!["GET", "HEAD", "OPTIONS", "TRACE"].includes(method)) {
    const csrfToken = getCookie("csrftoken");
    if (csrfToken) headers.set("X-CSRFToken", csrfToken);
  }

  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...fetchOptions,
      method,
      headers,
      credentials: "include",
    });
  } catch (cause) {
    const error = new Error("NETWORK_REQUEST_FAILED");
    error.status = 0;
    error.code = "NETWORK_ERROR";
    error.cause = cause;
    throw error;
  }

  if (!response.ok) {
    const contentType = response.headers.get("content-type") || "";
    const payload = contentType.includes("application/json")
      ? await response.json().catch(() => null)
      : await response.text().catch(() => "");
    const serverError = payload?.error || null;
    const message = serverError?.message || `API request failed: ${response.status}`;
    const error = new Error(message);
    error.status = response.status;
    error.code = serverError?.code || null;
    error.payload = payload;

    if (
      response.status === 401
      && !suppressAuthExpired
      && shouldNotifyAuthExpired(path, method)
    ) {
      window.dispatchEvent(new CustomEvent(AUTH_EXPIRED_EVENT, {
        detail: { path, method },
      }));
    }

    throw error;
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

function isUnsafeErrorMessage(message) {
  const text = String(message || "").trim();
  if (!text) return true;
  return (
    text === "NETWORK_REQUEST_FAILED"
    || text.startsWith("API request failed")
    || /<(!doctype|html|head|body|style|script|meta)\b/i.test(text)
    || /Traceback|Internal Server Error|OperationalError|ReferenceError|TypeError|SyntaxError/i.test(text)
  );
}

function safeServerMessage(message, fallback) {
  return isUnsafeErrorMessage(message) ? fallback : String(message).slice(0, 180);
}

export function getApiErrorState(error, fallbackTitle = "법률을 슥 가져오지 못하고 있어요") {
  const status = Number(error?.status || 0);
  const code = error?.code || "";
  const rawMessage = error?.message || "";
  const serverMessage = isUnsafeErrorMessage(rawMessage) ? "" : rawMessage;

  if (status === 0 || code === "NETWORK_ERROR") {
    return {
      status,
      code,
      title: "서버와 연결하지 못하고 있어요",
      message: "네트워크 상태나 백엔드 서버 실행 상태를 확인한 뒤 다시 요청해 주세요.",
      action: "retry",
      actionLabel: "다시 요청하기",
    };
  }

  if (status === 500) {
    return {
      status,
      code,
      title: "법률을 서버에서 슥 정리하지 못하고 있어요",
      message: safeServerMessage(serverMessage, "서버 내부 처리 중 문제가 생겼습니다. 잠시 후 다시 요청해 주세요."),
      action: "retry",
      actionLabel: "다시 요청하기",
    };
  }

  if (status === 503) {
    return {
      status,
      code,
      title: "AI가 잠시 응답하지 못하고 있어요",
      message: safeServerMessage(serverMessage, "요약 또는 검색 모델 연결이 불안정합니다. 잠시 후 다시 요청해 주세요."),
      action: "retry",
      actionLabel: "다시 요청하기",
    };
  }

  if ([502, 504].includes(status)) {
    return {
      status,
      code,
      title: "서버 응답이 잠시 불안정해요",
      message: "요청을 처리하는 중 서버 연결이 끊겼습니다. 잠시 후 다시 요청해 주세요.",
      action: "retry",
      actionLabel: "다시 요청하기",
    };
  }

  if (status === 404) {
    return {
      status,
      code,
      title: "요청한 법안을 찾지 못했어요",
      message: safeServerMessage(serverMessage, "법안이 삭제되었거나 아직 동기화되지 않았을 수 있습니다."),
      action: "retry",
      actionLabel: "다시 요청하기",
    };
  }

  if (status === 400) {
    return {
      status,
      code,
      title: "요청 내용을 다시 확인해 주세요",
      message: safeServerMessage(serverMessage, "검색어나 필터 조건이 올바르지 않습니다."),
      action: "retry",
      actionLabel: "다시 요청하기",
    };
  }

  return {
    status,
    code,
    title: fallbackTitle,
    message: safeServerMessage(serverMessage, "일시적인 문제가 발생했습니다. 다시 요청하거나 페이지를 새로고침해 주세요."),
    action: status ? "retry" : "reload",
    actionLabel: status ? "다시 요청하기" : "새로고침하기",
  };
}

export function getFrontendErrorState() {
  return {
    status: null,
    code: "FRONTEND_ERROR",
    title: "화면을 잠시 정리하지 못했어요",
    message: "브라우저에서 일시적인 문제가 발생했습니다. 새로고침하면 다시 시도할 수 있어요.",
    action: "reload",
    actionLabel: "새로고침하기",
  };
}

export function normalizeDate(value) {
  if (!value) return "";
  return String(value).slice(0, 10).replaceAll("-", ".");
}

export function normalizeStage(value) {
  const stage = String(value || "").trim();
  if (["proposed", "committee", "plenary", "passed"].includes(stage)) return stage;
  if (stage.includes("발의")) return "proposed";
  if (stage.includes("위원")) return "committee";
  if (stage.includes("본회의")) return "plenary";
  if (stage.includes("통과") || stage.includes("공포")) return "passed";
  return "proposed";
}

export function normalizeCat(category, index = 0) {
  const id = category?.id || category?.slug || category?.k || "etc";
  return {
    k: id,
    id,
    label: category?.label || id,
    accent: category?.accent ?? index === 0,
  };
}

export function normalizeCategory(category) {
  const id = category?.id || category?.slug || "all";
  return {
    id,
    label: category?.label || id,
    count: Number(category?.count || 0),
  };
}

export function normalizeSummary(summary) {
  if (Array.isArray(summary)) return summary.filter(Boolean);
  if (!summary) return [];
  return [String(summary)];
}

export function normalizeSimilar(similar = []) {
  return (Array.isArray(similar) ? similar : []).map((item) => ({
    targetId: String(item.targetId || item.target_id || ""),
    title: item.title || "",
    date: normalizeDate(item.date),
    stage: item.stage || "",
    score: Number(item.score || 0),
    rank: Number(item.rank || 0),
    method: item.method || "",
  })).filter((item) => item.title);
}

export function normalizeBill(bill, options = {}) {
  const id = String(bill?.id || bill?.bill_id || bill?.pk || "");
  const summary = normalizeSummary(bill?.summary);
  const comments = Number(bill?.comments ?? bill?.viewCount ?? bill?.view_count ?? 0);

  return {
    ...options,
    id,
    billNo: bill?.billNo || bill?.bill_no || "",
    title: bill?.title || "제목 없는 법안",
    cats: (bill?.categories || bill?.cats || []).map(normalizeCat),
    proposedAt: normalizeDate(bill?.proposedAt || bill?.proposed_at),
    proposer: bill?.proposer || "",
    committee: bill?.committee || "",
    stage: normalizeStage(bill?.stage),
    resultStatus: bill?.resultStatus || bill?.result_status || "pending",
    resultText: bill?.resultText || bill?.result_text || "",
    summary,
    summaryText: summary.join(" "),
    description: bill?.description || bill?.billDescription || bill?.bill_description || bill?.content || "",
    content: bill?.content || "",
    comments,
    viewCount: Number(bill?.viewCount ?? bill?.view_count ?? comments),
    impact: bill?.impact || "",
    similar: normalizeSimilar(bill?.similar),
    similarLoaded: Boolean(bill?.similarLoaded || (Array.isArray(bill?.similar) && bill.similar.length)),
    detailLink: bill?.detailLink || bill?.detail_link || "",
    syncedAt: bill?.syncedAt || bill?.synced_at || "",
  };
}

export function normalizePost(post, options = {}) {
  const id = Number(post?.idx ?? post?.id ?? 0);
  const billId = String(post?.bill ?? post?.billId ?? post?.bill_id ?? "");

  return {
    ...options,
    id,
    idx: id,
    title: post?.title || "제목 없는 포스트",
    content: post?.content || "",
    billId,
    billTitle: post?.billTitle || post?.bill_title || "",
    userIdx: Number(post?.userIdx ?? post?.user_id ?? 0),
    nickname: post?.nickname || "익명",
    createdAt: post?.createdAt || post?.created_at || "",
    updatedAt: post?.updatedAt || post?.updated_at || "",
    viewCount: Number(post?.viewCount ?? post?.view_count ?? 0),
    commentCount: Number(post?.commentCount ?? post?.comment_count ?? 0),
  };
}

export function normalizeComment(comment, options = {}) {
  const id = Number(comment?.idx ?? comment?.id ?? 0);
  const replies = Array.isArray(comment?.replies)
    ? comment.replies.map((reply) => normalizeComment(reply))
    : [];

  return {
    ...options,
    id,
    idx: id,
    postIdx: Number(comment?.postIdx ?? comment?.post_id ?? 0),
    postTitle: comment?.postTitle || comment?.post_title || "",
    postBillId: String(comment?.postBillId ?? comment?.post_bill_id ?? ""),
    billTitle: comment?.billTitle || comment?.bill_title || "",
    parent: comment?.parent ?? comment?.parent_id ?? null,
    userIdx: Number(comment?.userIdx ?? comment?.user_id ?? 0),
    nickname: comment?.nickname || "익명",
    content: comment?.content || "",
    createdAt: comment?.createdAt || comment?.created_at || "",
    updatedAt: comment?.updatedAt || comment?.updated_at || "",
    viewCount: Number(comment?.viewCount ?? comment?.view_count ?? 0),
    isDeleted: Boolean(comment?.isDeleted ?? comment?.is_deleted ?? false),
    replies,
  };
}

export const lawApi = {
  getCategories() {
    return request("/api/categories");
  },
  getHomePicks() {
    return request("/api/home/picks");
  },
  getBills(params = {}) {
    const query = new URLSearchParams(params).toString();
    return request(`/api/bills${query ? `?${query}` : ""}`);
  },
  getBill(id) {
    return request(`/api/bills/${id}`);
  },
  getSimilarBills(id, params = {}) {
    const query = new URLSearchParams(params).toString();
    return request(`/api/bills/${id}/similar${query ? `?${query}` : ""}`);
  },
  searchBills(query) {
    return request("/api/search", {
      method: "POST",
      body: JSON.stringify({ query }),
    });
  },
  explainSearch(query) {
    return request("/api/search/explain", {
      method: "POST",
      body: JSON.stringify({ query }),
    });
  },
  sendChat(message, sessionKey) {
    return request("/api/chat", {
      method: "POST",
      body: JSON.stringify({ message, session_key: sessionKey }),
    });
  },
};

export const postApi = {
  getPosts(params = {}) {
    const query = new URLSearchParams(params).toString();
    return request(`/api/posts${query ? `?${query}` : ""}`);
  },
  getPost(idx) {
    return request(`/api/posts/${idx}`);
  },
  createPost(post) {
    return request("/api/posts", {
      method: "POST",
      body: JSON.stringify(post),
    });
  },
  updatePost(idx, changes) {
    return request(`/api/posts/${idx}`, {
      method: "PATCH",
      body: JSON.stringify(changes),
    });
  },
  deletePost(idx) {
    return request(`/api/posts/${idx}`, { method: "DELETE" });
  },
  getComments(postIdx) {
    return request(`/api/posts/${postIdx}/comments`);
  },
  getUserComments(userIdx, params = {}) {
    const query = new URLSearchParams(params).toString();
    return request(`/api/users/${userIdx}/comments${query ? `?${query}` : ""}`);
  },
  createComment(postIdx, comment) {
    return request(`/api/posts/${postIdx}/comments`, {
      method: "POST",
      body: JSON.stringify(comment),
    });
  },
  updateComment(idx, changes) {
    return request(`/api/comments/${idx}`, {
      method: "PATCH",
      body: JSON.stringify(changes),
    });
  },
  deleteComment(idx) {
    return request(`/api/comments/${idx}`, { method: "DELETE" });
  },
};

export const authApi = {
  getCsrfToken() {
    return request("/api/auth/csrf");
  },
  login(id, password) {
    return request("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ id, password }),
    });
  },
  logout() {
    return request("/api/auth/logout", { method: "POST" });
  },
  getCurrentAccount(options = {}) {
    return request("/api/auth/me", {
      suppressAuthExpired: true,
      ...options,
    });
  },
  getAccount(idx) {
    return request(`/api/users/${idx}`);
  },
  signup(account) {
    return request("/api/accounts", {
      method: "POST",
      body: JSON.stringify(account),
    });
  },
  updateAccount(idx, changes) {
    return request(`/api/accounts/${idx}`, {
      method: "PATCH",
      body: JSON.stringify(changes),
    });
  },
  deleteAccount(idx) {
    return request(`/api/accounts/${idx}`, { method: "DELETE" });
  },
};
