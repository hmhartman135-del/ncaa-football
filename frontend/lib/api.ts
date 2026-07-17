import axios from "axios";

function makeBaseUrl(raw: string | undefined): string {
  // NEXT_PUBLIC_API_URL (set in Vercel's project settings) is the real source of
  // truth in production. This fallback only matters if that's unset — swap the
  // Railway URL below for your actual deployed backend domain once you have one.
  const fallback =
    typeof window !== "undefined" && window.location.hostname !== "localhost"
      ? "https://ncaa-football-production.up.railway.app"
      : "http://localhost:8004";
  const url = raw || fallback;
  return url.startsWith("http://") || url.startsWith("https://") ? url : "https://" + url;
}

const api = axios.create({ baseURL: makeBaseUrl(process.env.NEXT_PUBLIC_API_URL) });

export const getTeams = (params?: Record<string, string | number>) =>
  api.get("/teams", { params }).then((r) => r.data);

export const getTeam = (school: string, params?: Record<string, string | number>) =>
  api.get(`/teams/${encodeURIComponent(school)}`, { params }).then((r) => r.data);

export const getTeamAnalysis = (school: string) =>
  api.get(`/teams/${encodeURIComponent(school)}/analysis`).then((r) => r.data);

export const getTeamDiscussion = (school: string) =>
  api.get(`/teams/${encodeURIComponent(school)}/discuss`).then((r) => r.data);

export const getStandings = (params?: Record<string, string | number>) =>
  api.get("/standings", { params }).then((r) => r.data);

export const getRankings = (params?: Record<string, string | number>) =>
  api.get("/standings/rankings", { params }).then((r) => r.data);

export const getPlayers = (params?: Record<string, string | number>) =>
  api.get("/players", { params }).then((r) => r.data);

export const getPlayer = (id: number) =>
  api.get(`/players/${id}`).then((r) => r.data);

export const getPlayerProfile = (ref: string | number) =>
  api.get(`/players/profile/${ref}`).then((r) => r.data);

export const getMetrics = () =>
  api.get("/analytics/metrics").then((r) => r.data);

export const getLeaderboard = (params?: Record<string, string | number>) =>
  api.get("/analytics/leaderboard", { params }).then((r) => r.data);

export const getTeamMetrics = () =>
  api.get("/analytics/team-metrics").then((r) => r.data);

export const getTeamFullStats = (school: string, params?: Record<string, string | number>) =>
  api.get(`/analytics/team/${encodeURIComponent(school)}`, { params }).then((r) => r.data);

export const getTeamStatsAnalysis = (school: string, params?: Record<string, string | number>) =>
  api.get(`/analytics/team/${encodeURIComponent(school)}/discuss`, { params }).then((r) => r.data);

export const getTeamStatRankings = (params?: Record<string, string | number>) =>
  api.get("/analytics/team-rankings", { params }).then((r) => r.data);

export const getScoutingReport = (playerId: number) =>
  api.get(`/scouting/report/${playerId}`).then((r) => r.data);

export const comparePlayers = (player_ids: number[], team_context?: string) =>
  api.post("/scouting/compare", { player_ids, team_context: team_context || null }).then((r) => r.data);

export const getRoster = (team: string, params?: Record<string, string | number>) =>
  api.get(`/roster/${encodeURIComponent(team)}`, { params }).then((r) => r.data);

export const getCurrentRoster = (team: string) =>
  api.get(`/roster/${encodeURIComponent(team)}/current`).then((r) => r.data);

export const analyzeRoster = (team: string, params?: Record<string, string | number>) =>
  api.get(`/roster/${encodeURIComponent(team)}/analyze`, { params }).then((r) => r.data);

export const getRecruits = (params?: Record<string, string | number>) =>
  api.get("/recruiting", { params }).then((r) => r.data);

export const getTeamRecruits = (school: string, params?: Record<string, string | number>) =>
  api.get(`/recruiting/team/${encodeURIComponent(school)}`, { params }).then((r) => r.data);

export const getRecruitingRankings = (params?: Record<string, string | number>) =>
  api.get("/recruiting/rankings", { params }).then((r) => r.data);

export const get247TeamRankings = (params?: Record<string, string | number>) =>
  api.get("/recruiting/rankings/247", { params }).then((r) => r.data);

export const getTransferPortal = (params?: Record<string, string | number | boolean>) =>
  api.get("/transfer-portal", { params }).then((r) => r.data);

export const getTeamPortalActivity = (school: string) =>
  api.get(`/transfer-portal/team/${encodeURIComponent(school)}`).then((r) => r.data);

export const getPortalRankings = (params?: Record<string, string | number>) =>
  api.get("/transfer-portal/rankings", { params }).then((r) => r.data);

export const gradePortalEntry = (entryId: number) =>
  api.post(`/transfer-portal/${entryId}/grade`).then((r) => r.data);

export const getDraftEligible = (params?: Record<string, string | number>) =>
  api.get("/draft/eligible", { params }).then((r) => r.data);

export const getDraftBoard = (params?: Record<string, string | number>) =>
  api.get("/draft/board", { params }).then((r) => r.data);

export const gradeDraftProspect = (playerId: number, params?: Record<string, string | number>) =>
  api.post(`/draft/grade/${playerId}`, null, { params }).then((r) => r.data);

export const getGameWeeks = (params?: Record<string, string | number>) =>
  api.get("/games/weeks", { params }).then((r) => r.data);

export const getGamesForWeek = (params?: Record<string, string | number>) =>
  api.get("/games", { params }).then((r) => r.data);

export const predictGame = (gameId: number, force?: boolean) =>
  api.post(`/games/${gameId}/predict`, null, { params: force ? { force: true } : undefined }).then((r) => r.data);

export const predictTeamSeason = (school: string, force?: boolean) =>
  api.post(`/teams/${encodeURIComponent(school)}/predict-season`, null, { params: force ? { force: true } : undefined }).then((r) => r.data);

export const getRankingWeeks = (params?: Record<string, string | number>) =>
  api.get("/rankings/weeks", { params }).then((r) => r.data);

export const getApPoll = (params?: Record<string, string | number>) =>
  api.get("/rankings/poll", { params }).then((r) => r.data);

export const getAiTop25 = (params?: Record<string, string | number>) =>
  api.get("/rankings/ai-top25", { params }).then((r) => r.data);

export const generateAiTop25 = (params?: Record<string, string | number>) =>
  api.post("/rankings/ai-top25", null, { params }).then((r) => r.data);

export const triggerIngest = () =>
  api.post("/admin/ingest").then((r) => r.data);

export default api;
