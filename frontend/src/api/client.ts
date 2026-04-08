const BASE = "/api";

async function json<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

function patch<T>(url: string, body: Record<string, unknown>): Promise<T> {
  return json(url, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

function post<T>(url: string, body: Record<string, unknown>): Promise<T> {
  return json(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export interface DashboardStats {
  total_songs: number;
  total_sessions: number;
  total_takes: number;
  total_audio_files: number;
  songs_by_status: Record<string, number>;
  songs_by_project: Record<string, number>;
  gig_ready_songs: number;
  unrated_takes: number;
}

export interface RoadmapTask {
  id: number;
  phase: number;
  phase_title: string | null;
  category: string | null;
  task_text: string;
  completed: boolean;
  sort_order: number;
}

export interface RoadmapPhase {
  phase: number;
  phase_title: string;
  tasks: RoadmapTask[];
  total: number;
  completed: number;
}

export interface DashboardResponse {
  stats: DashboardStats;
  roadmap: RoadmapPhase[];
}

export interface Song {
  id: number;
  title: string;
  artist: string | null;
  project: string;
  is_original: boolean;
  status: string;
  times_practiced: number;
  notes: string | null;
  has_audio: boolean;
  take_count: number;
}

export interface Take {
  id: number;
  session_id: number;
  song_id: number | null;
  clip_name: string;
  source_video: string | null;
  start_time: string | null;
  end_time: string | null;
  video_path: string | null;
  audio_path: string | null;
  rating: number | null;
  notes: string | null;
  song_title: string | null;
  session_date: string | null;
}

export interface AudioFile {
  id: number;
  song_id: number | null;
  file_path: string;
  file_type: string | null;
  source: string | null;
  version: string | null;
}

export interface SongDetail extends Song {
  takes: Take[];
  audio_files: AudioFile[];
}

export interface Session {
  id: number;
  date: string;
  project: string;
  folder_path: string;
  notes: string | null;
  take_count: number;
}

export interface SessionDetail extends Session {
  takes: Take[];
}

export interface ContentPost {
  id: number;
  title: string;
  song_id: number | null;
  take_id: number | null;
  platform: string | null;
  post_type: string | null;
  scheduled_date: string | null;
  status: string;
  caption: string | null;
  notes: string | null;
  song_title: string | null;
}

export interface SetlistItem {
  id: number;
  song_id: number;
  position: number;
  duration_minutes: number;
  notes: string | null;
  song_title: string | null;
  song_artist: string | null;
  song_status: string | null;
}

export interface Setlist {
  id: number;
  name: string;
  description: string | null;
  config: string;
  items: SetlistItem[];
  total_minutes: number;
  song_count: number;
}

export const api = {
  dashboard: {
    get: () => json<DashboardResponse>(`${BASE}/dashboard`),
  },
  repertoire: {
    list: (params?: Record<string, string>) => {
      const qs = params ? "?" + new URLSearchParams(params).toString() : "";
      return json<Song[]>(`${BASE}/repertoire${qs}`);
    },
    get: (id: number) => json<SongDetail>(`${BASE}/repertoire/${id}`),
    update: (id: number, data: Record<string, unknown>) =>
      patch<Song>(`${BASE}/repertoire/${id}`, data),
  },
  sessions: {
    list: () => json<Session[]>(`${BASE}/sessions`),
    get: (id: number) => json<SessionDetail>(`${BASE}/sessions/${id}`),
  },
  takes: {
    update: (id: number, data: Record<string, unknown>) =>
      patch<Take>(`${BASE}/sessions/takes/${id}`, data),
    best: (minRating = 1) =>
      json<Take[]>(`${BASE}/sessions/takes/best?min_rating=${minRating}`),
  },
  roadmap: {
    toggleTask: (id: number, completed: boolean) =>
      patch<RoadmapTask>(`${BASE}/dashboard/roadmap/${id}`, { completed }),
  },
  content: {
    list: () => json<ContentPost[]>(`${BASE}/content/posts`),
    create: (data: Record<string, unknown>) =>
      post<ContentPost>(`${BASE}/content/posts`, data),
    update: (id: number, data: Record<string, unknown>) =>
      patch<ContentPost>(`${BASE}/content/posts/${id}`, data),
  },
  setlists: {
    list: () => json<Setlist[]>(`${BASE}/setlists`),
    get: (id: number) => json<Setlist>(`${BASE}/setlists/${id}`),
    create: (data: Record<string, unknown>) => post<Setlist>(`${BASE}/setlists`, data),
    update: (id: number, data: Record<string, unknown>) => patch<Setlist>(`${BASE}/setlists/${id}`, data),
    delete: (id: number) => json<{ ok: boolean }>(`${BASE}/setlists/${id}`, { method: "DELETE" }),
  },
  media: {
    takeAudioUrl: (takeId: number) => `${BASE}/media/take/${takeId}/audio`,
    audioFileUrl: (audioFileId: number) => `${BASE}/media/audio/${audioFileId}`,
  },
};
