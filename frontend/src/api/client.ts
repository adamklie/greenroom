const BASE = "/api";

// 403 toast hook. Set once in App.tsx so any forbidden mutation surfaces a
// "viewer mode — ask the admin for edit access" message. Kept as a single
// module-level callback so the fetch wrapper doesn't have to thread it
// through every call site.
let forbiddenHandler: ((message: string) => void) | null = null;
export function setForbiddenHandler(fn: ((message: string) => void) | null) {
  forbiddenHandler = fn;
}

async function json<T>(url: string, init?: RequestInit): Promise<T> {
  // credentials: 'include' is critical — without it the browser strips
  // the greenroom_session cookie and every authed request becomes 401.
  // Same-origin in dev (proxy) and prod (single server), so 'include' is
  // safe here.
  const res = await fetch(url, { credentials: "include", ...init });
  if (res.status === 403 && forbiddenHandler) {
    forbiddenHandler("Viewer mode — ask the admin for edit access");
  }
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

function put<T>(url: string, body: Record<string, unknown>): Promise<T> {
  return json(url, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

// --- Types ---

export interface DashboardStats {
  total_songs: number;
  total_sessions: number;
  total_takes: number;
  total_audio_files: number;
  songs_by_type: Record<string, number>;
  songs_by_status: Record<string, number>;
  songs_by_project: Record<string, number>;
  unrated_takes: number;
}

export interface RecentSong {
  id: number; title: string; artist: string | null;
  type: string; status: string; created_at: string | null;
}
export interface RecentAudioFile {
  id: number; identifier: string | null; file_path: string; file_type: string;
  song_id: number | null; song_title: string | null;
  session_id: number | null; session_date: string | null;
  created_at: string | null; uploaded_at: string | null; recorded_at: string | null;
}
export interface RecentSession {
  id: number; date: string; folder_path: string;
  clip_count: number; created_at: string | null;
}
export interface DashboardResponse {
  stats: DashboardStats;
  recent_songs: RecentSong[];
  recent_audio_files: RecentAudioFile[];
  recent_sessions: RecentSession[];
}

export interface Song {
  id: number;
  title: string;
  artist: string | null;
  type: string; // cover, original, idea
  project: string;
  status: string;
  key: string | null;
  tempo_bpm: number | null;
  tuning: string | null;
  vibe: string | null;
  lyrics: string | null;
  notes: string | null;
  times_practiced: number;
  reference_audio_file_id: number | null;
  promoted_from_id: number | null;
  has_audio: boolean;
  take_count: number;
  tags: string[];
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
  rating_overall: number | null;
  rating_vocals: number | null;
  rating_guitar: number | null;
  rating_drums: number | null;
  rating_tone: number | null;
  rating_timing: number | null;
  rating_energy: number | null;
  notes: string | null;
  song_title: string | null;
  session_date: string | null;
  tags: string[];
}

export interface AudioFile {
  id: number;
  song_id: number | null;
  file_path: string;
  file_type: string | null;
  identifier: string | null;
  submitted_file_name: string | null;
  source: string | null;
  role: string | null;
  version: string | null;
  session_id: number | null;
  clip_name: string | null;
  source_file: string | null;
  start_time: string | null;
  end_time: string | null;
  video_path: string | null;
  rating_overall: number | null;
  rating_vocals: number | null;
  rating_guitar: number | null;
  rating_drums: number | null;
  rating_tone: number | null;
  rating_timing: number | null;
  rating_energy: number | null;
  rating_keys: number | null;
  rating_bass: number | null;
  rating_mix: number | null;
  rating_other: number | null;
  notes: string | null;
  created_at: string | null;
  uploaded_at: string | null;
  recorded_at: string | null;
  song_title: string | null;
  song_artist: string | null;
  song_type: string | null;
  session_date: string | null;
  file_exists: boolean | null;
}

export interface LyricsVersion {
  id: number;
  song_id: number;
  version_number: number;
  lyrics_text: string;
  change_note: string | null;
}

export interface SongTab {
  id: number;
  song_id: number;
  label: string | null;
  instrument: string | null;
  file_path: string;
  file_format: string | null;
  original_filename: string | null;
  is_primary: boolean;
  notes: string | null;
  created_at: string | null;
}

export interface SongDetail extends Song {
  takes: Take[];
  audio_files: AudioFile[];
  lyrics_versions: LyricsVersion[];
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
  audio_files: AudioFile[];
}

export interface TagItem {
  id: number;
  name: string;
  category: string;
  color: string | null;
  is_predefined: boolean;
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

// --- API ---

export interface CurrentUser {
  id: number;
  email: string;
  role: "viewer" | "editor" | "admin";
}

export const api = {
  health: {
    get: () => json<{ status: string; app: string; version: string }>(`${BASE}/health`),
  },
  auth: {
    me: () => json<CurrentUser>(`${BASE}/auth/me`),
    requestMagicLink: (email: string) =>
      post<{ ok: boolean; message: string }>(`${BASE}/auth/request`, { email }),
    logout: () => post<{ ok: boolean }>(`${BASE}/auth/logout`, {}),
  },
  dashboard: {
    get: () => json<DashboardResponse>(`${BASE}/dashboard`),
  },
  songs: {
    list: (params?: Record<string, string>) => {
      const qs = params ? "?" + new URLSearchParams(params).toString() : "";
      return json<Song[]>(`${BASE}/songs${qs}`);
    },
    get: (id: number) => json<SongDetail>(`${BASE}/songs/${id}`),
    create: (data: Record<string, unknown>) => post<Song>(`${BASE}/songs`, data),
    update: (id: number, data: Record<string, unknown>) =>
      patch<Song>(`${BASE}/songs/${id}`, data),
    delete: (id: number) =>
      json<{ ok: boolean }>(`${BASE}/songs/${id}`, { method: "DELETE" }),
    updateLyrics: (id: number, lyrics: string, changeNote?: string) =>
      put<Song>(`${BASE}/songs/${id}/lyrics`, { lyrics, change_note: changeNote }),
    lyricsVersions: (id: number) =>
      json<LyricsVersion[]>(`${BASE}/songs/${id}/lyrics/versions`),
    addTag: (id: number, tagName: string) =>
      post<{ ok: boolean; tags: string[] }>(`${BASE}/songs/${id}/tags?tag_name=${encodeURIComponent(tagName)}`, {}),
    removeTag: (id: number, tagName: string) =>
      json<{ ok: boolean; tags: string[] }>(`${BASE}/songs/${id}/tags/${encodeURIComponent(tagName)}`, { method: "DELETE" }),
    promote: (id: number) => post<Song>(`${BASE}/songs/${id}/promote`, {}),
  },
  sessions: {
    list: () => json<Session[]>(`${BASE}/sessions`),
    get: (id: number) => json<SessionDetail>(`${BASE}/sessions/${id}`),
  },
  takes: {
    update: (id: number, data: Record<string, unknown>) =>
      patch<Take>(`${BASE}/sessions/takes/${id}`, data),
    best: (minRating = 1, dimension = "overall") =>
      json<Take[]>(`${BASE}/sessions/takes/best?min_rating=${minRating}&dimension=${dimension}`),
    addTag: (id: number, tagName: string) =>
      post<{ ok: boolean; tags: string[] }>(`${BASE}/sessions/takes/${id}/tags?tag_name=${encodeURIComponent(tagName)}`, {}),
    removeTag: (id: number, tagName: string) =>
      json<{ ok: boolean; tags: string[] }>(`${BASE}/sessions/takes/${id}/tags/${encodeURIComponent(tagName)}`, { method: "DELETE" }),
  },
  tags: {
    list: (category?: string) => {
      const qs = category ? `?category=${category}` : "";
      return json<TagItem[]>(`${BASE}/tags${qs}`);
    },
    create: (data: Record<string, unknown>) => post<TagItem>(`${BASE}/tags`, data),
  },
  setlists: {
    list: () => json<Setlist[]>(`${BASE}/setlists`),
    get: (id: number) => json<Setlist>(`${BASE}/setlists/${id}`),
    create: (data: Record<string, unknown>) => post<Setlist>(`${BASE}/setlists`, data),
    update: (id: number, data: Record<string, unknown>) => patch<Setlist>(`${BASE}/setlists/${id}`, data),
    delete: (id: number) => json<{ ok: boolean }>(`${BASE}/setlists/${id}`, { method: "DELETE" }),
  },
  options: {
    list: (category?: string) => {
      const qs = category ? `?category=${category}` : "";
      return json<{ id: number; category: string; value: string; label: string | null; is_default: boolean }[]>(`${BASE}/options${qs}`);
    },
    create: (category: string, value: string, label?: string) =>
      post<{ id: number; category: string; value: string; label: string | null }>(
        `${BASE}/options`, { category, value, label }),
    delete: (id: number) =>
      json<{ ok: boolean }>(`${BASE}/options/${id}`, { method: "DELETE" }),
  },
  audioFiles: {
    list: (params?: Record<string, string>) => {
      const qs = params ? "?" + new URLSearchParams(params).toString() : "";
      return json<AudioFile[]>(`${BASE}/audio-files${qs}`);
    },
    get: (id: number) => json<AudioFile>(`${BASE}/audio-files/${id}`),
    update: (id: number, data: Record<string, unknown>) =>
      patch<AudioFile>(`${BASE}/audio-files/${id}`, data),
    delete: (id: number) =>
      json<{ ok: boolean }>(`${BASE}/audio-files/${id}`, { method: "DELETE" }),
    trim: (id: number, startTime: number, endTime: number) =>
      post<AudioFile>(`${BASE}/audio-files/${id}/trim`, { start_time: startTime, end_time: endTime }),
    extractAudio: (id: number) =>
      post<AudioFile>(`${BASE}/audio-files/${id}/extract-audio`, {}),
  },
  tabs: {
    list: (songId?: number) => {
      const qs = songId !== undefined ? `?song_id=${songId}` : "";
      return json<SongTab[]>(`${BASE}/tabs${qs}`);
    },
    get: (id: number) => json<SongTab>(`${BASE}/tabs/${id}`),
    update: (id: number, data: Record<string, unknown>) =>
      patch<SongTab>(`${BASE}/tabs/${id}`, data),
    delete: (id: number) =>
      json<{ ok: boolean }>(`${BASE}/tabs/${id}`, { method: "DELETE" }),
    fileUrl: (id: number) => `${BASE}/tabs/${id}/file`,
  },
  backup: {
    create: () => post<{ ok: boolean; path: string }>(`${BASE}/backup/create`, {}),
    list: () => json<{ backups: { filename: string; path: string; size_mb: number; created: string }[] }>(`${BASE}/backup/list`),
    restore: (filename: string) => post<{ ok: boolean }>(`${BASE}/backup/restore/${filename}`, {}),
    hashFiles: () => post<{ total: number; newly_hashed: number; already_hashed: number; missing_files: number }>(`${BASE}/backup/hash-files`, {}),
    autoHeal: () => post<{ checked: number; healed: number; unresolvable: number }>(`${BASE}/backup/auto-heal`, {}),
    export: () => post<{ ok: boolean; path: string; songs: number; takes: number; setlists: number }>(`${BASE}/backup/export`, {}),
  },
  browse: {
    list: (path = "~") =>
      json<{
        path: string; parent: string; error?: string;
        entries: { name: string; path: string; type: "directory" | "video"; size_mb?: number }[];
      }>(`${BASE}/browse?path=${encodeURIComponent(path)}`),
  },
  gopro: {
    listVideos: (directory: string) =>
      json<{ files: { filename: string; path: string; size_mb: number; extension: string }[]; directory: string }>(
        `${BASE}/gopro/list-videos?directory=${encodeURIComponent(directory)}`
      ),
    analyze: (videoPath: string, opts?: { dropDb?: number; minGap?: number; minClip?: number }) =>
      post<{
        video_path: string; duration_seconds: number; median_db: number; threshold_db: number;
        proposed_clips: { start_seconds: number; end_seconds: number; duration_seconds: number; suggested_name: string }[];
        energy_profile: { time: number; db: number }[];
      }>(`${BASE}/gopro/analyze`, {
        video_path: videoPath,
        drop_db: opts?.dropDb ?? 6.0,
        min_gap_duration: opts?.minGap ?? 2.0,
        min_clip_duration: opts?.minClip ?? 30.0,
      }),
    process: (data: {
      source_path: string; session_date: string; project?: string;
      clips: { start_seconds: number; end_seconds: number; clip_name: string; song_id?: number | null }[];
      existing_session_id?: number | null;
    }) => post<{
      session_id: number; session_date: string; clips_processed: number;
      audio_extracted: number; errors: string[]; cuts_txt_path: string;
    }>(`${BASE}/gopro/process`, data),
  },
  analytics: {
    practiceFrequency: () => json<{ date: string; takes: number }[]>(`${BASE}/analytics/practice-frequency`),
    ratingTrends: (songId?: number, dimension = "overall") => {
      const params = new URLSearchParams({ dimension });
      if (songId) params.set("song_id", String(songId));
      return json<{ date: string; avg_rating: number; take_count: number }[]>(`${BASE}/analytics/rating-trends?${params}`);
    },
    skillRadar: () => json<Record<string, { average: number | null; count: number }>>(`${BASE}/analytics/skill-radar`),
    songProgress: () => json<{
      song_id: number; title: string; type: string; status: string;
      take_count: number; last_practiced: string | null; avg_rating: number | null;
    }[]>(`${BASE}/analytics/song-progress`),
    sessionSummary: () => json<{
      session_id: number; date: string; take_count: number; matched_takes: number; avg_overall: number | null;
    }[]>(`${BASE}/analytics/session-summary`),
    statusFunnel: () => json<{ status: string; count: number }[]>(`${BASE}/analytics/status-funnel`),
  },
  files: {
    healthCheck: () => json<{
      total_broken: number;
      broken_links: { table: string; record_id: number; field: string; path: string; song_title: string | null }[];
    }>(`${BASE}/files/health`),
    moveAudioFile: (id: number, newPath: string) =>
      post<{ ok: boolean; new_path: string }>(`${BASE}/files/audio/${id}/move`, { new_path: newPath }),
    consolidateOne: (id: number) =>
      post<{ ok: boolean; new_path: string }>(`${BASE}/files/audio/${id}/consolidate`, {}),
    consolidateAll: () =>
      post<{ moved: number; skipped: number; errors: string[] }>(`${BASE}/files/consolidate-all`, {}),
  },
  media: {
    takeAudioUrl: (takeId: number) => `${BASE}/media/take/${takeId}/audio`,
    takeVideoUrl: (takeId: number) => `${BASE}/media/take/${takeId}/video`,
    audioFileUrl: (audioFileId: number) => `${BASE}/media/audio/${audioFileId}`,
  },
};
