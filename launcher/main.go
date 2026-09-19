package main

import (
	"archive/zip"
	"bytes"
	"crypto/aes"
	"crypto/cipher"
	"crypto/sha256"
	"embed"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"sort"
	"strings"
	"sync"
	"time"
)

const discoveryPort = 39720

//go:embed payload.enc
var payloadFS embed.FS

const payloadAAD = "DungeonWorld::payload::v1"

// The payload key is split so the executable does not contain one obvious key string.
// This is anti-tamper/obfuscation hardening, not an absolute DRM guarantee.
var payloadKeyA = [32]byte{0x9c, 0x21, 0x73, 0xa8, 0xf0, 0x44, 0x8b, 0x5d, 0x11, 0x6f, 0xc2, 0x3a, 0x94, 0xe7, 0x50, 0x1d, 0x6a, 0xbe, 0x03, 0xd1, 0x87, 0x59, 0x2c, 0xf4, 0x38, 0xa1, 0x6d, 0x0b, 0xe5, 0x72, 0x49, 0xbc}
var payloadKeyB = [32]byte{0x31, 0xd4, 0x06, 0x5f, 0x82, 0xae, 0x19, 0xc7, 0xb8, 0x2a, 0x75, 0x90, 0x4d, 0x13, 0xe6, 0xa4, 0xcf, 0x55, 0xb9, 0x2e, 0x64, 0xf3, 0x80, 0x17, 0xad, 0x4c, 0xd8, 0x61, 0x09, 0xfe, 0x36, 0x42}

var (
	payloadOnce  sync.Once
	payloadPlain []byte
	payloadErr   error
)

type statusState struct {
	Phase    string           `json:"phase"`
	Message  string           `json:"message"`
	Ready    bool             `json:"ready"`
	Running  bool             `json:"running"`
	Port     int              `json:"port"`
	LocalURL string           `json:"local_url,omitempty"`
	LAN      []networkAddress `json:"addresses,omitempty"`
	Error    string           `json:"error,omitempty"`
	Attached bool             `json:"attached"`
}

type networkAddress struct {
	IP   string `json:"ip"`
	URL  string `json:"url"`
	Kind string `json:"kind"`
}

type campaignInfo struct {
	Code         string `json:"code"`
	CampaignName string `json:"campaign_name"`
	GMName       string `json:"gm_name"`
	PlayerCount  int    `json:"player_count"`
	MaxPlayers   int    `json:"max_players"`
	CreatedAt    string `json:"created_at,omitempty"`
	UpdatedAt    string `json:"updated_at,omitempty"`
}

type classInfo struct {
	Name  string   `json:"name"`
	Races []string `json:"races"`
}

type joinInfo struct {
	RoomCode         string      `json:"room_code"`
	CampaignName     string      `json:"campaign_name"`
	GMName           string      `json:"gm_name"`
	PlayerCount      int         `json:"player_count"`
	MaxPlayers       int         `json:"max_players"`
	Full             bool        `json:"full"`
	PasswordRequired bool        `json:"password_required"`
	Classes          []classInfo `json:"classes"`
}

type pyCommand struct {
	Exe  string
	Args []string
}

type recentClient struct {
	Host         string `json:"host"`
	Room         string `json:"room"`
	CampaignName string `json:"campaign_name,omitempty"`
	GMName       string `json:"gm_name,omitempty"`
	DisplayName  string `json:"display_name,omitempty"`
	PlayerToken  string `json:"player_token"`
	CharacterID  int    `json:"character_id,omitempty"`
	LastUsed     string `json:"last_used"`
	Online       bool   `json:"online"`
	Status       string `json:"status,omitempty"`
}

type invitePayload struct {
	Format  int    `json:"f"`
	Host    string `json:"h"`
	Port    int    `json:"p"`
	Room    string `json:"r"`
	Version string `json:"v"`
	Build   string `json:"b"`
}

type discoveryCampaign struct {
	Host         string `json:"host"`
	Port         int    `json:"port"`
	Room         string `json:"room"`
	CampaignName string `json:"campaign_name"`
	GMName       string `json:"gm_name"`
	PlayerCount  int    `json:"player_count"`
	MaxPlayers   int    `json:"max_players"`
	Full         bool   `json:"full"`
}

type discoveryResponse struct {
	Magic     string         `json:"magic"`
	Version   string         `json:"version"`
	Build     string         `json:"build"`
	Instance  string         `json:"instance"`
	Port      int            `json:"port"`
	Campaigns []campaignInfo `json:"campaigns"`
}

type activeCampaignInfo struct {
	Active       bool   `json:"active"`
	RoomCode     string `json:"room_code"`
	CampaignName string `json:"campaign_name"`
	GMName       string `json:"gm_name"`
	PlayerCount  int    `json:"player_count"`
	MaxPlayers   int    `json:"max_players"`
	Full         bool   `json:"full"`
	Instance     string `json:"instance"`
}

type pingInfo struct {
	OK       bool   `json:"ok"`
	Version  string `json:"version"`
	Build    string `json:"build"`
	Uptime   int    `json:"uptime"`
	Instance string `json:"instance"`
}

var (
	version          = embeddedPayloadValue("VERSION")
	buildID          = embeddedPayloadValue("BUILD_ID")
	mu               sync.Mutex
	st               = statusState{Phase: "idle", Message: "호스트 또는 클라이언트를 선택하세요."}
	serverCmd        *exec.Cmd
	ownsServer       bool
	serverPort       int
	healthMisses     int
	healthSuccesses  int
	intentionalStop  bool
	restartScheduled bool
	restartAttempts  int
	discoveryOnce    sync.Once
	activeRoom       string
	launcherBase     string
)

func main() {
	mux := http.NewServeMux()
	mux.HandleFunc("/", launcherPage)
	mux.HandleFunc("/api/status", apiStatus)
	mux.HandleFunc("/api/host", apiHost)
	mux.HandleFunc("/api/host/campaigns", apiHostCampaigns)
	mux.HandleFunc("/api/host/create", apiHostCreate)
	mux.HandleFunc("/api/host/open", apiHostOpen)
	mux.HandleFunc("/api/host/invites", apiHostInvites)
	mux.HandleFunc("/api/stop", apiStop)
	mux.HandleFunc("/api/client/probe", apiClientProbe)
	mux.HandleFunc("/api/client/join", apiClientJoin)
	mux.HandleFunc("/api/client/resume", apiClientResume)
	mux.HandleFunc("/api/client/reconnect", apiClientReconnect)
	mux.HandleFunc("/api/discover", apiDiscover)
	mux.HandleFunc("/api/recent", apiRecent)
	mux.HandleFunc("/api/recent/delete", apiRecentDelete)
	mux.HandleFunc("/api/recent/clear", apiRecentClear)
	mux.HandleFunc("/api/reset/browser", apiResetBrowser)
	mux.HandleFunc("/api/reset/all", apiResetAll)
	mux.HandleFunc("/api/quit", apiQuit)

	listenAddr := strings.TrimSpace(os.Getenv("DW_LAUNCHER_ADDR"))
	if listenAddr == "" {
		listenAddr = "127.0.0.1:0"
	}
	ln, err := net.Listen("tcp", listenAddr)
	if err != nil {
		return
	}
	launchURL := "http://" + ln.Addr().String() + "/"
	mu.Lock()
	launcherBase = strings.TrimRight(launchURL, "/")
	mu.Unlock()
	go func() { _ = http.Serve(ln, mux) }()
	go healthWatchdog()
	time.Sleep(100 * time.Millisecond)
	if os.Getenv("DW_NO_BROWSER") != "1" {
		openBrowser(launchURL)
	}
	select {}
}

func launcherPage(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path != "/" {
		http.NotFound(w, r)
		return
	}
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.Header().Set("Cache-Control", "no-store")
	html := strings.ReplaceAll(launcherHTML, "__DISPLAY_VERSION__", launcherDisplayVersion())
	html = strings.ReplaceAll(html, "__APP_VERSION__", launcherAppVersion())
	_, _ = io.WriteString(w, html)
}

func apiStatus(w http.ResponseWriter, r *http.Request) {
	mu.Lock()
	x := st
	mu.Unlock()
	writeJSON(w, x)
}

func apiHost(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "POST only", http.StatusMethodNotAllowed)
		return
	}
	mu.Lock()
	if st.Phase == "starting" || st.Running {
		x := st
		mu.Unlock()
		writeJSON(w, x)
		return
	}
	intentionalStop = false
	restartScheduled = false
	restartAttempts = 0
	healthMisses = 0
	healthSuccesses = 0
	st = statusState{Phase: "starting", Message: "호스트 서버를 준비하고 있습니다…"}
	mu.Unlock()
	go startHost()
	writeJSON(w, map[string]any{"ok": true})
}

func apiHostCampaigns(w http.ResponseWriter, r *http.Request) {
	base, err := currentServerBase()
	if err != nil {
		writeJSON(w, map[string]any{"ok": false, "error": err.Error(), "campaigns": []campaignInfo{}})
		return
	}
	var out struct {
		Campaigns []campaignInfo `json:"campaigns"`
	}
	if err := getJSON(base+"/api/local/campaigns", &out, 1600*time.Millisecond); err != nil {
		writeJSON(w, map[string]any{"ok": false, "error": "캠페인 목록을 읽지 못했습니다: " + err.Error(), "campaigns": []campaignInfo{}})
		return
	}
	writeJSON(w, map[string]any{"ok": true, "campaigns": out.Campaigns})
}

func apiHostCreate(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "POST only", http.StatusMethodNotAllowed)
		return
	}
	var body struct {
		GMName       string `json:"gm_name"`
		CampaignName string `json:"campaign_name"`
		Password     string `json:"password"`
		MaxPlayers   int    `json:"max_players"`
	}
	_ = json.NewDecoder(r.Body).Decode(&body)
	body.GMName = strings.TrimSpace(body.GMName)
	body.CampaignName = strings.TrimSpace(body.CampaignName)
	if body.GMName == "" || body.CampaignName == "" {
		writeJSON(w, map[string]any{"ok": false, "error": "GM 이름과 캠페인 이름을 입력하세요."})
		return
	}
	if body.MaxPlayers == 0 {
		body.MaxPlayers = 4
	}
	if body.MaxPlayers < 2 || body.MaxPlayers > 8 {
		writeJSON(w, map[string]any{"ok": false, "error": "최대 플레이어 수는 2명부터 8명까지 설정할 수 있습니다."})
		return
	}
	base, err := currentServerBase()
	if err != nil {
		writeJSON(w, map[string]any{"ok": false, "error": err.Error()})
		return
	}
	var created struct {
		RoomCode     string `json:"room_code"`
		GMToken      string `json:"gm_token"`
		CampaignName string `json:"campaign_name"`
	}
	code, err := postJSON(base+"/api/rooms", map[string]any{"gm_name": body.GMName, "campaign_name": body.CampaignName, "password": body.Password, "max_players": body.MaxPlayers}, "", &created, 8*time.Second)
	if err != nil || code >= 300 {
		writeJSON(w, map[string]any{"ok": false, "error": httpErr(code, err, "캠페인을 생성하지 못했습니다.")})
		return
	}
	mu.Lock()
	activeRoom = strings.ToUpper(created.RoomCode)
	mu.Unlock()
	gameURL, err := issueSessionURL(base, created.RoomCode, created.GMToken)
	if err != nil {
		writeJSON(w, map[string]any{"ok": false, "error": err.Error()})
		return
	}
	invites := buildInvites(created.RoomCode)
	writeJSON(w, map[string]any{"ok": true, "room": created.RoomCode, "campaign_name": created.CampaignName, "url": gameURL, "invites": invites})
}

func apiHostOpen(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "POST only", http.StatusMethodNotAllowed)
		return
	}
	var body struct {
		Room string `json:"room"`
	}
	_ = json.NewDecoder(r.Body).Decode(&body)
	room := strings.ToUpper(strings.TrimSpace(body.Room))
	base, err := currentServerBase()
	if err != nil {
		writeJSON(w, map[string]any{"ok": false, "error": err.Error()})
		return
	}
	var resumed struct {
		RoomCode     string `json:"room_code"`
		CampaignName string `json:"campaign_name"`
		GMName       string `json:"gm_name"`
		GMToken      string `json:"gm_token"`
	}
	code, err := postJSON(base+"/api/local/campaigns/"+url.PathEscape(room)+"/resume", map[string]any{}, "", &resumed, 4*time.Second)
	if err != nil || code >= 300 {
		writeJSON(w, map[string]any{"ok": false, "error": httpErr(code, err, "캠페인을 열지 못했습니다.")})
		return
	}
	mu.Lock()
	activeRoom = strings.ToUpper(resumed.RoomCode)
	mu.Unlock()
	gameURL, err := issueSessionURL(base, resumed.RoomCode, resumed.GMToken)
	if err != nil {
		writeJSON(w, map[string]any{"ok": false, "error": err.Error()})
		return
	}
	writeJSON(w, map[string]any{"ok": true, "url": gameURL, "room": resumed.RoomCode, "campaign_name": resumed.CampaignName, "invites": buildInvites(resumed.RoomCode)})
}

func apiHostInvites(w http.ResponseWriter, r *http.Request) {
	room := strings.ToUpper(strings.TrimSpace(r.URL.Query().Get("room")))
	if room == "" {
		writeJSON(w, map[string]any{"ok": false, "error": "캠페인 코드가 필요합니다."})
		return
	}
	base, err := currentServerBase()
	if err != nil {
		writeJSON(w, map[string]any{"ok": false, "error": err.Error()})
		return
	}
	if err := activateCampaign(base, room); err != nil {
		writeJSON(w, map[string]any{"ok": false, "error": err.Error()})
		return
	}
	writeJSON(w, map[string]any{"ok": true, "room": room, "invites": buildInvites(room)})
}

func apiStop(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "POST only", http.StatusMethodNotAllowed)
		return
	}
	mu.Lock()
	intentionalStop = true
	restartScheduled = false
	restartAttempts = 0
	activeRoom = ""
	port := serverPort
	cmd := serverCmd
	own := ownsServer
	mu.Unlock()
	if port > 0 {
		base := fmt.Sprintf("http://127.0.0.1:%d", port)
		clearActiveCampaign(base)
		c := http.Client{Timeout: 1400 * time.Millisecond}
		resp, err := c.Post(base+"/api/local/server-stop", "application/json", bytes.NewBufferString("{}"))
		if err == nil && resp != nil {
			_ = resp.Body.Close()
		}
	}
	if own && cmd != nil && cmd.Process != nil {
		go func() {
			time.Sleep(900 * time.Millisecond)
			mu.Lock()
			still := serverCmd == cmd
			mu.Unlock()
			if still {
				_ = cmd.Process.Kill()
			}
		}()
	}
	mu.Lock()
	st = statusState{Phase: "idle", Message: "호스트 서버를 종료했습니다."}
	serverCmd = nil
	ownsServer = false
	serverPort = 0
	healthMisses = 0
	healthSuccesses = 0
	mu.Unlock()
	writeJSON(w, map[string]any{"ok": true})
}

func apiClientProbe(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "POST only", http.StatusMethodNotAllowed)
		return
	}
	var body struct {
		Invite string `json:"invite"`
		Host   string `json:"host"`
		Room   string `json:"room"`
	}
	_ = json.NewDecoder(r.Body).Decode(&body)
	host, room, err := resolveClientTarget(body.Invite, body.Host, body.Room)
	if err != nil {
		writeJSON(w, map[string]any{"ok": false, "error": err.Error()})
		return
	}
	info, err := probeCampaign(host, room, 2500*time.Millisecond)
	if err != nil {
		writeJSON(w, map[string]any{"ok": false, "error": err.Error()})
		return
	}
	writeJSON(w, map[string]any{"ok": true, "host": host, "room": room, "info": info})
}

func apiClientJoin(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "POST only", http.StatusMethodNotAllowed)
		return
	}
	var body struct {
		Host        string `json:"host"`
		Room        string `json:"room"`
		DisplayName string `json:"display_name"`
		Password    string `json:"password"`
	}
	_ = json.NewDecoder(r.Body).Decode(&body)
	host, err := normalizeHost(body.Host)
	if err != nil {
		writeJSON(w, map[string]any{"ok": false, "error": err.Error()})
		return
	}
	room := strings.ToUpper(strings.TrimSpace(body.Room))
	info, err := probeCampaign(host, room, 2200*time.Millisecond)
	if err != nil {
		writeJSON(w, map[string]any{"ok": false, "error": err.Error()})
		return
	}
	var joined struct {
		PlayerToken string `json:"player_token"`
		CharacterID int    `json:"character_id"`
	}
	status, err := postJSON(host+"/api/rooms/"+url.PathEscape(room)+"/join", map[string]any{
		"display_name": strings.TrimSpace(body.DisplayName), "password": body.Password,
	}, "", &joined, 8*time.Second)
	if err != nil || status >= 300 {
		writeJSON(w, map[string]any{"ok": false, "error": httpErr(status, err, "캠페인 참가에 실패했습니다.")})
		return
	}
	gameURL, err := issueSessionURL(host, room, joined.PlayerToken)
	if err != nil {
		writeJSON(w, map[string]any{"ok": false, "error": err.Error()})
		return
	}
	rec := recentClient{Host: host, Room: room, CampaignName: info.CampaignName, GMName: info.GMName, DisplayName: strings.TrimSpace(body.DisplayName), PlayerToken: joined.PlayerToken, CharacterID: joined.CharacterID, LastUsed: time.Now().Format(time.RFC3339), Online: true, Status: "온라인"}
	saveRecentClient(rec)
	writeJSON(w, map[string]any{"ok": true, "url": gameURL, "campaign_name": info.CampaignName})
}

func apiClientResume(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "POST only", http.StatusMethodNotAllowed)
		return
	}
	var body struct {
		Host string `json:"host"`
		Room string `json:"room"`
	}
	_ = json.NewDecoder(r.Body).Decode(&body)
	host, err := normalizeHost(body.Host)
	if err != nil {
		writeJSON(w, map[string]any{"ok": false, "error": err.Error()})
		return
	}
	room := strings.ToUpper(strings.TrimSpace(body.Room))
	rec, ok := findRecentClient(host, room)
	if !ok || rec.PlayerToken == "" {
		writeJSON(w, map[string]any{"ok": false, "error": "이 PC에 해당 캐릭터의 재접속 정보가 없습니다. 새 캠페인 참가를 이용하세요."})
		return
	}
	target := host
	info, probeErr := probeCampaign(target, room, 1800*time.Millisecond)
	if probeErr != nil {
		found := discoverRoom(room, 1800*time.Millisecond)
		if found == "" {
			writeJSON(w, map[string]any{"ok": false, "error": "이 캠페인은 현재 열려 있지 않습니다. GM이 캠페인을 연 뒤 다시 시도하세요."})
			return
		}
		info, probeErr = probeCampaign(found, room, 1800*time.Millisecond)
		if probeErr != nil {
			writeJSON(w, map[string]any{"ok": false, "error": "이 캠페인은 현재 열려 있지 않습니다. GM이 캠페인을 연 뒤 다시 시도하세요."})
			return
		}
		target = found
	}
	gameURL, err := issueSessionURL(target, room, rec.PlayerToken)
	if err != nil {
		writeJSON(w, map[string]any{"ok": false, "error": "재접속 인증에 실패했습니다. 인증이 바뀌었다면 새 캠페인 참가 또는 재접속 코드를 이용하세요."})
		return
	}
	rec.Host = target
	if info != nil {
		rec.CampaignName = info.CampaignName
		rec.GMName = info.GMName
	}
	rec.LastUsed = time.Now().Format(time.RFC3339)
	rec.Online = true
	rec.Status = "온라인"
	saveRecentClient(rec)
	writeJSON(w, map[string]any{"ok": true, "url": gameURL, "host": target})
}

func apiClientReconnect(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "POST only", http.StatusMethodNotAllowed)
		return
	}
	var body struct {
		Host          string `json:"host"`
		ReconnectCode string `json:"reconnect_code"`
	}
	_ = json.NewDecoder(r.Body).Decode(&body)
	raw := strings.ToUpper(strings.TrimSpace(body.ReconnectCode))
	parts := strings.SplitN(raw, "-", 2)
	if len(parts) != 2 || len(strings.TrimSpace(parts[0])) != 6 || strings.TrimSpace(parts[1]) == "" {
		writeJSON(w, map[string]any{"ok": false, "error": "GM에게 받은 재접속 코드를 입력하세요. 예: ABC123-XXXXXXXX"})
		return
	}
	room := strings.ToUpper(strings.TrimSpace(parts[0]))
	hostText := strings.TrimSpace(body.Host)
	host := ""
	var err error
	if hostText != "" {
		host, err = normalizeHost(hostText)
	} else {
		host = discoverRoom(room, 2200*time.Millisecond)
		if host == "" {
			err = fmt.Errorf("같은 LAN에서 캠페인을 찾지 못했습니다. VPN/다른 집이라면 서버 주소를 함께 입력하세요.")
		}
	}
	if err != nil {
		writeJSON(w, map[string]any{"ok": false, "error": err.Error()})
		return
	}
	info, err := probeCampaign(host, room, 2200*time.Millisecond)
	if err != nil {
		writeJSON(w, map[string]any{"ok": false, "error": err.Error()})
		return
	}
	var restored struct {
		OK          bool   `json:"ok"`
		PlayerToken string `json:"player_token"`
		CharacterID int    `json:"character_id"`
		DisplayName string `json:"display_name"`
	}
	status, err := postJSON(host+"/api/rooms/"+url.PathEscape(room)+"/reconnect", map[string]any{"reconnect_code": raw}, "", &restored, 6*time.Second)
	if err != nil || status >= 300 || restored.PlayerToken == "" {
		writeJSON(w, map[string]any{"ok": false, "error": httpErr(status, err, "재접속 코드가 올바르지 않거나 이미 사용되었습니다.")})
		return
	}
	gameURL, err := issueSessionURL(host, room, restored.PlayerToken)
	if err != nil {
		writeJSON(w, map[string]any{"ok": false, "error": err.Error()})
		return
	}
	rec := recentClient{Host: host, Room: room, CampaignName: info.CampaignName, GMName: info.GMName, DisplayName: restored.DisplayName, PlayerToken: restored.PlayerToken, CharacterID: restored.CharacterID, LastUsed: time.Now().Format(time.RFC3339), Online: true, Status: "온라인"}
	saveRecentClient(rec)
	writeJSON(w, map[string]any{"ok": true, "url": gameURL, "host": host, "room": room, "campaign_name": info.CampaignName})
}

func apiDiscover(w http.ResponseWriter, r *http.Request) {
	xs := discoverLAN(2200 * time.Millisecond)
	writeJSON(w, map[string]any{"ok": true, "campaigns": xs})
}

func apiRecent(w http.ResponseWriter, r *http.Request) {
	xs := loadRecentClients()
	out := make([]recentClient, len(xs))
	var wg sync.WaitGroup
	for i := range xs {
		i := i
		wg.Add(1)
		go func() {
			defer wg.Done()
			x := xs[i]
			x.Online = false
			x.Status = "오프라인"
			if info, err := probeCampaign(x.Host, x.Room, 550*time.Millisecond); err == nil {
				x.Online = true
				x.Status = "온라인"
				x.CampaignName = info.CampaignName
				x.GMName = info.GMName
			}
			x.PlayerToken = ""
			out[i] = x
		}()
	}
	wg.Wait()
	writeJSON(w, map[string]any{"recent": out})
}

func apiRecentDelete(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "POST only", http.StatusMethodNotAllowed)
		return
	}
	var body struct{ Host, Room string }
	_ = json.NewDecoder(r.Body).Decode(&body)
	host, err := normalizeHost(body.Host)
	if err == nil {
		removeRecentClient(host, strings.ToUpper(strings.TrimSpace(body.Room)))
	}
	writeJSON(w, map[string]any{"ok": true})
}

func apiRecentClear(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "POST only", http.StatusMethodNotAllowed)
		return
	}
	writeRecentClients([]recentClient{})
	writeJSON(w, map[string]any{"ok": true})
}

func apiResetBrowser(w http.ResponseWriter, r *http.Request) {
	base, err := currentServerBase()
	if err != nil {
		writeJSON(w, map[string]any{"ok": false, "error": "브라우저 초기화를 위해 호스트 서버를 먼저 시작하세요."})
		return
	}
	writeJSON(w, map[string]any{"ok": true, "url": base + "/?mode=reset"})
}

func apiResetAll(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "POST only", http.StatusMethodNotAllowed)
		return
	}
	mu.Lock()
	intentionalStop = true
	restartScheduled = false
	restartAttempts = 0
	activeRoom = ""
	cmd := serverCmd
	own := ownsServer
	port := serverPort
	mu.Unlock()
	if port > 0 {
		base := fmt.Sprintf("http://127.0.0.1:%d", port)
		clearActiveCampaign(base)
		c := http.Client{Timeout: 1000 * time.Millisecond}
		if resp, err := c.Post(base+"/api/local/server-stop", "application/json", bytes.NewBufferString("{}")); err == nil && resp != nil {
			_ = resp.Body.Close()
		}
	}
	if own && cmd != nil && cmd.Process != nil {
		time.Sleep(300 * time.Millisecond)
		_ = cmd.Process.Kill()
	}
	root := configRoot()
	_ = os.RemoveAll(filepath.Join(root, "data"))
	_ = os.Remove(recentPath())
	mu.Lock()
	st = statusState{Phase: "idle", Message: "캠페인 DB와 최근 참가 기록을 초기화했습니다."}
	serverCmd = nil
	ownsServer = false
	serverPort = 0
	healthMisses = 0
	healthSuccesses = 0
	mu.Unlock()
	writeJSON(w, map[string]any{"ok": true})
}

func apiQuit(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, map[string]any{"ok": true})
	go func() {
		time.Sleep(150 * time.Millisecond)
		mu.Lock()
		intentionalStop = true
		restartScheduled = false
		cmd := serverCmd
		own := ownsServer
		mu.Unlock()
		if own && cmd != nil && cmd.Process != nil {
			mu.Lock()
			port := serverPort
			mu.Unlock()
			if port > 0 {
				c := http.Client{Timeout: 700 * time.Millisecond}
				if resp, err := c.Post(fmt.Sprintf("http://127.0.0.1:%d/api/local/server-stop", port), "application/json", bytes.NewBufferString("{}")); err == nil && resp != nil {
					_ = resp.Body.Close()
				}
				time.Sleep(250 * time.Millisecond)
			}
			if cmd.ProcessState == nil || !cmd.ProcessState.Exited() {
				_ = cmd.Process.Kill()
			}
		}
		os.Exit(0)
	}()
}

func currentServerBase() (string, error) {
	mu.Lock()
	ready, port := st.Running && st.Ready, serverPort
	mu.Unlock()
	if !ready || port <= 0 {
		return "", fmt.Errorf("호스트 서버가 아직 준비되지 않았습니다.")
	}
	return fmt.Sprintf("http://127.0.0.1:%d", port), nil
}

func clearActiveCampaign(base string) {
	req, err := http.NewRequest(http.MethodDelete, strings.TrimRight(base, "/")+"/api/local/active-campaign", nil)
	if err != nil {
		return
	}
	c := http.Client{Timeout: 900 * time.Millisecond}
	if resp, err := c.Do(req); err == nil && resp != nil {
		_ = resp.Body.Close()
	}
}

func activateCampaign(base, room string) error {
	room = strings.ToUpper(strings.TrimSpace(room))
	if room == "" {
		return fmt.Errorf("캠페인 코드가 필요합니다.")
	}
	var out activeCampaignInfo
	status, err := postJSON(strings.TrimRight(base, "/")+"/api/local/active-campaign/"+url.PathEscape(room), map[string]any{}, "", &out, 1800*time.Millisecond)
	if err != nil || status >= 300 || !out.Active || !strings.EqualFold(out.RoomCode, room) {
		return fmt.Errorf("캠페인을 온라인 상태로 전환하지 못했습니다.")
	}
	mu.Lock()
	activeRoom = room
	mu.Unlock()
	return nil
}

func normalizeHost(raw string) (string, error) {
	h := strings.TrimSpace(raw)
	if h == "" {
		return "", fmt.Errorf("호스트 주소를 입력하세요.")
	}
	if !strings.Contains(h, "://") {
		h = "http://" + h
	}
	u, err := url.Parse(h)
	if err != nil || u.Hostname() == "" {
		return "", fmt.Errorf("호스트 주소 형식을 확인하세요.")
	}
	if u.Scheme != "http" && u.Scheme != "https" {
		return "", fmt.Errorf("http 또는 https 주소만 사용할 수 있습니다.")
	}
	if u.Port() == "" {
		u.Host = net.JoinHostPort(u.Hostname(), "8000")
	}
	u.Path, u.RawQuery, u.Fragment = "", "", ""
	return strings.TrimRight(u.String(), "/"), nil
}

func encodeInvite(host string, port int, room string) string {
	p := invitePayload{Format: 2, Host: host, Port: port, Room: strings.ToUpper(room), Version: version, Build: embeddedBuildID()}
	b, _ := json.Marshal(p)
	return "DW2-" + base64.RawURLEncoding.EncodeToString(b)
}

func decodeInvite(code string) (invitePayload, error) {
	raw := strings.TrimSpace(code)
	if !strings.HasPrefix(strings.ToUpper(raw), "DW2-") {
		return invitePayload{}, fmt.Errorf("Dungeon World 초대코드 형식이 아닙니다.")
	}
	b, err := base64.RawURLEncoding.DecodeString(raw[4:])
	if err != nil {
		return invitePayload{}, fmt.Errorf("초대코드를 읽지 못했습니다.")
	}
	var p invitePayload
	if json.Unmarshal(b, &p) != nil || p.Format != 2 || p.Host == "" || p.Port < 1 || p.Room == "" {
		return invitePayload{}, fmt.Errorf("초대코드 내용이 올바르지 않습니다.")
	}
	if p.Version != version {
		return invitePayload{}, fmt.Errorf("서버 버전이 다릅니다. 초대코드: %s / 현재 런처: %s", p.Version, version)
	}
	if p.Build != "" && p.Build != embeddedBuildID() {
		return invitePayload{}, fmt.Errorf("같은 버전의 다른 빌드입니다. GM과 같은 EXE 파일을 사용해주세요.")
	}
	return p, nil
}

func resolveClientTarget(invite, rawHost, rawRoom string) (string, string, error) {
	if strings.TrimSpace(invite) != "" {
		p, err := decodeInvite(invite)
		if err != nil {
			return "", "", err
		}
		host, err := normalizeHost(fmt.Sprintf("http://%s:%d", p.Host, p.Port))
		return host, strings.ToUpper(p.Room), err
	}
	host, err := normalizeHost(rawHost)
	if err != nil {
		return "", "", err
	}
	room := strings.ToUpper(strings.TrimSpace(rawRoom))
	if room == "" {
		return "", "", fmt.Errorf("캠페인 코드를 입력하세요.")
	}
	return host, room, nil
}

func buildInvites(room string) []map[string]any {
	mu.Lock()
	port := serverPort
	addresses := append([]networkAddress{}, st.LAN...)
	mu.Unlock()
	out := make([]map[string]any, 0, len(addresses))
	seenIP := map[string]bool{}
	seenKind := map[string]bool{}
	for _, a := range addresses {
		if a.IP == "" || seenIP[a.IP] {
			continue
		}
		// One ordinary LAN invite is enough even when Windows exposes the same
		// network through more than one adapter. Distinct VPN routes remain useful.
		group := strings.TrimSpace(a.Kind)
		if group == "" {
			group = "네트워크"
		}
		if group == "로컬 LAN" && seenKind[group] {
			continue
		}
		seenIP[a.IP] = true
		seenKind[group] = true
		out = append(out, map[string]any{"ip": a.IP, "kind": a.Kind, "url": a.URL, "code": encodeInvite(a.IP, port, room)})
	}
	// No loopback invite is shown. A player on the host PC can simply use the
	// already-open host session; portable invite codes are for network routes.
	return out
}

func probeCampaign(host, room string, timeout time.Duration) (*joinInfo, error) {
	var ping pingInfo
	if err := getJSON(host+"/api/ping", &ping, timeout); err != nil {
		return nil, fmt.Errorf("호스트 서버에 연결할 수 없습니다. 주소와 네트워크 연결을 확인하세요.")
	}
	if !ping.OK || ping.Version != version {
		return nil, fmt.Errorf("서버 버전이 다릅니다. 서버: %s / 런처: %s", ping.Version, version)
	}
	if ping.Build != embeddedBuildID() {
		return nil, fmt.Errorf("같은 %s이지만 빌드가 다릅니다. GM과 같은 EXE 파일을 사용해주세요.", launcherDisplayVersion())
	}
	var active activeCampaignInfo
	if err := getJSON(host+"/api/active-campaign", &active, timeout); err != nil {
		return nil, fmt.Errorf("호스트에서 현재 열린 캠페인을 확인하지 못했습니다.")
	}
	if !active.Active || !strings.EqualFold(active.RoomCode, room) {
		if !active.Active {
			return nil, fmt.Errorf("호스트 서버는 실행 중이지만 아직 열린 캠페인이 없습니다.")
		}
		return nil, fmt.Errorf("현재 호스트에서 이 캠페인은 열려 있지 않습니다. GM이 해당 캠페인을 열어야 접속할 수 있습니다.")
	}
	var info joinInfo
	status, err := getJSONStatus(host+"/api/rooms/"+url.PathEscape(room)+"/join-info", &info, timeout)
	if err != nil || status != http.StatusOK {
		if status == http.StatusNotFound {
			return nil, fmt.Errorf("해당 캠페인을 찾을 수 없습니다.")
		}
		return nil, fmt.Errorf("캠페인 정보를 확인하지 못했습니다.")
	}
	return &info, nil
}

func issueSessionURL(host, room, token string) (string, error) {
	var out struct {
		URL string `json:"url"`
	}
	status, err := postJSON(host+"/api/rooms/"+url.PathEscape(room)+"/session-ticket", map[string]any{}, token, &out, 3500*time.Millisecond)
	if err != nil || status >= 300 || out.URL == "" {
		return "", fmt.Errorf("게임 접속 세션을 만들지 못했습니다. 재접속 정보가 만료되었을 수 있습니다.")
	}
	if strings.HasPrefix(out.URL, "http://") || strings.HasPrefix(out.URL, "https://") {
		return out.URL, nil
	}
	return strings.TrimRight(host, "/") + "/" + strings.TrimLeft(out.URL, "/"), nil
}

func startHost() {
	if p := findExistingServer(); p > 0 {
		setReady(p, true)
		startDiscoveryResponder()
		return
	}
	setStatus("starting", "게임 파일을 확인하는 중…", false, false, 0, "")
	appDir, dataDir, err := preparePayload()
	if err != nil {
		fail(err)
		return
	}
	py, err := findPython()
	if err != nil {
		fail(fmt.Errorf("Python 3.11 이상을 찾지 못했습니다. (%v)", err))
		return
	}
	setStatus("starting", "필수 패키지를 확인하는 중…", false, false, 0, "")
	if err := runPython(py, appDir, "-c", "import fastapi,uvicorn,pydantic,multipart"); err != nil {
		setStatus("starting", "첫 실행입니다. 필요한 Python 패키지를 설치하는 중…", false, false, 0, "")
		_ = runPython(py, appDir, "-m", "ensurepip", "--upgrade")
		if err := runPython(py, appDir, "-m", "pip", "install", "-r", "requirements.txt"); err != nil {
			fail(fmt.Errorf("필수 패키지 자동 설치 실패: %v", err))
			return
		}
	}
	port, err := chooseServerPort()
	if err != nil {
		fail(err)
		return
	}
	logDir := filepath.Join(dataDir, "logs")
	_ = os.MkdirAll(logDir, 0755)
	logFile, _ := os.OpenFile(filepath.Join(logDir, "server.log"), os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0644)
	args := append(append([]string{}, py.Args...), "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", fmt.Sprint(port))
	cmd := exec.Command(py.Exe, args...)
	cmd.Dir = appDir
	mu.Lock()
	controlBase := launcherBase
	mu.Unlock()
	cmd.Env = append(os.Environ(), "PYTHONUTF8=1", "DW_DB="+filepath.Join(dataDir, "dungeonworld.db"), fmt.Sprintf("DW_PORT=%d", port), "DW_LAUNCHER_BASE="+controlBase)
	hideProcess(cmd)
	if logFile != nil {
		cmd.Stdout, cmd.Stderr = logFile, logFile
	}
	if err := cmd.Start(); err != nil {
		fail(fmt.Errorf("서버 시작 실패: %v", err))
		return
	}
	mu.Lock()
	serverCmd, ownsServer, serverPort = cmd, true, port
	healthMisses = 0
	healthSuccesses = 0
	mu.Unlock()
	go func() {
		err := cmd.Wait()
		if logFile != nil {
			_ = logFile.Close()
		}
		mu.Lock()
		current := serverCmd == cmd
		stopRequested := intentionalStop
		if current {
			serverCmd = nil
			ownsServer = false
			serverPort = 0
			healthMisses = 0
			healthSuccesses = 0
		}
		mu.Unlock()
		if !current {
			return
		}
		if stopRequested {
			mu.Lock()
			if st.Phase != "idle" {
				st = statusState{Phase: "idle", Message: "호스트 서버가 종료되었습니다."}
			}
			mu.Unlock()
			return
		}
		reason := "서버 프로세스가 종료되었습니다."
		if err != nil {
			reason = fmt.Sprintf("서버 프로세스 오류: %v", err)
		}
		scheduleHostRestart(reason)
	}()
	setStatus("starting", "서버 응답을 기다리는 중…", false, true, port, "")
	deadline := time.Now().Add(18 * time.Second)
	for time.Now().Before(deadline) {
		if p, ok := pingAt(port); ok && p.Version == version && p.Build == embeddedBuildID() {
			setReady(port, false)
			startDiscoveryResponder()
			return
		}
		time.Sleep(250 * time.Millisecond)
	}
	mu.Lock()
	still := serverCmd == cmd
	mu.Unlock()
	if still && cmd.Process != nil {
		_ = cmd.Process.Kill()
	}
	fail(fmt.Errorf("서버가 시작되지 않았습니다. 로그: %s", filepath.Join(logDir, "server.log")))
}

func scheduleHostRestart(reason string) {
	mu.Lock()
	if intentionalStop || restartScheduled {
		mu.Unlock()
		return
	}
	if restartAttempts >= 3 {
		st = statusState{Phase: "error", Message: "호스트 서버 자동 복구를 중단했습니다.", Error: reason + " 수동으로 호스트 서버를 다시 시작해주세요."}
		serverCmd = nil
		ownsServer = false
		serverPort = 0
		mu.Unlock()
		return
	}
	restartAttempts++
	attempt := restartAttempts
	restartScheduled = true
	serverCmd = nil
	ownsServer = false
	serverPort = 0
	healthMisses = 0
	healthSuccesses = 0
	st = statusState{Phase: "starting", Message: fmt.Sprintf("호스트 서버 연결이 끊겨 자동 복구 중입니다. (%d/3)", attempt), Error: reason}
	mu.Unlock()
	delay := time.Duration(1<<(attempt-1)) * time.Second
	go func() {
		time.Sleep(delay)
		mu.Lock()
		if intentionalStop {
			restartScheduled = false
			mu.Unlock()
			return
		}
		restartScheduled = false
		mu.Unlock()
		startHost()
	}()
}

func healthWatchdog() {
	ticker := time.NewTicker(2 * time.Second)
	defer ticker.Stop()
	for range ticker.C {
		mu.Lock()
		running, ready, port, own, stopRequested := st.Running, st.Ready, serverPort, ownsServer, intentionalStop
		cmd := serverCmd
		mu.Unlock()
		if !running || !ready || port <= 0 {
			continue
		}
		p, ok := pingAt(port)
		valid := ok && p.Version == version && p.Build == embeddedBuildID()
		if valid {
			mu.Lock()
			healthMisses = 0
			healthSuccesses++
			if healthSuccesses >= 6 {
				restartAttempts = 0
			}
			mu.Unlock()
			continue
		}
		mu.Lock()
		healthSuccesses = 0
		healthMisses++
		misses := healthMisses
		mu.Unlock()
		if misses < 3 {
			continue
		}
		if own && !stopRequested {
			if cmd != nil && cmd.Process != nil {
				_ = cmd.Process.Kill()
			}
			scheduleHostRestart("서버가 연속 3회 상태 확인에 응답하지 않았습니다.")
		} else {
			mu.Lock()
			st = statusState{Phase: "idle", Message: "연결된 호스트 서버가 더 이상 응답하지 않습니다."}
			serverCmd = nil
			ownsServer = false
			serverPort = 0
			healthMisses = 0
			mu.Unlock()
		}
	}
}

func chooseServerPort() (int, error) {
	for p := 8000; p <= 8099; p++ {
		ln, err := net.Listen("tcp", fmt.Sprintf("127.0.0.1:%d", p))
		if err == nil {
			_ = ln.Close()
			return p, nil
		}
	}
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		return 0, fmt.Errorf("사용 가능한 서버 포트를 찾지 못했습니다.")
	}
	p := ln.Addr().(*net.TCPAddr).Port
	_ = ln.Close()
	return p, nil
}

func findExistingServer() int {
	expected := embeddedBuildID()
	for p := 8000; p <= 8099; p++ {
		info, ok := pingAt(p)
		if !ok || info.Version != version {
			continue
		}
		if info.Build == expected {
			return p
		}
		// 같은 버전명으로 다시 빌드된 오래된 payload 서버는 자동 종료한다.
		c := http.Client{Timeout: 700 * time.Millisecond}
		if resp, err := c.Post(fmt.Sprintf("http://127.0.0.1:%d/api/local/server-stop", p), "application/json", bytes.NewBufferString("{}")); err == nil && resp != nil {
			_ = resp.Body.Close()
		}
	}
	return 0
}

func pingAt(port int) (pingInfo, bool) {
	c := http.Client{Timeout: 350 * time.Millisecond}
	resp, err := c.Get(fmt.Sprintf("http://127.0.0.1:%d/api/ping", port))
	if err != nil {
		return pingInfo{}, false
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return pingInfo{}, false
	}
	var x pingInfo
	if json.NewDecoder(resp.Body).Decode(&x) != nil || !x.OK {
		return pingInfo{}, false
	}
	return x, true
}

func payloadKey() []byte {
	k := make([]byte, 32)
	for i := range k {
		k[i] = payloadKeyA[i] ^ payloadKeyB[i]
	}
	return k
}

func decryptedPayload() ([]byte, error) {
	payloadOnce.Do(func() {
		b, err := payloadFS.ReadFile("payload.enc")
		if err != nil {
			payloadErr = err
			return
		}
		const magic = "DWENC1"
		if len(b) < len(magic)+12 || string(b[:len(magic)]) != magic {
			payloadErr = fmt.Errorf("암호화된 게임 파일 형식이 올바르지 않습니다.")
			return
		}
		block, err := aes.NewCipher(payloadKey())
		if err != nil {
			payloadErr = err
			return
		}
		var gcm cipher.AEAD
		gcm, err = cipher.NewGCM(block)
		if err != nil {
			payloadErr = err
			return
		}
		nonceStart := len(magic)
		nonceEnd := nonceStart + gcm.NonceSize()
		if len(b) <= nonceEnd {
			payloadErr = fmt.Errorf("암호화된 게임 파일이 손상되었습니다.")
			return
		}
		nonce := b[nonceStart:nonceEnd]
		ciphertext := b[nonceEnd:]
		payloadPlain, payloadErr = gcm.Open(nil, nonce, ciphertext, []byte(payloadAAD))
		if payloadErr != nil {
			payloadErr = fmt.Errorf("게임 파일 무결성 검증에 실패했습니다: %w", payloadErr)
		}
	})
	return payloadPlain, payloadErr
}

func embeddedPayloadValue(name string) string {
	b, err := decryptedPayload()
	if err != nil {
		return ""
	}
	zr, err := zip.NewReader(bytes.NewReader(b), int64(len(b)))
	if err != nil {
		return ""
	}
	for _, f := range zr.File {
		if filepath.ToSlash(f.Name) != name {
			continue
		}
		rc, err := f.Open()
		if err != nil {
			return ""
		}
		data, _ := io.ReadAll(io.LimitReader(rc, 256))
		_ = rc.Close()
		return strings.TrimSpace(string(data))
	}
	return ""
}

func embeddedBuildID() string { return buildID }

func launcherAppVersion() string {
	v := strings.TrimSpace(version)
	if i := strings.IndexByte(v, '-'); i >= 0 {
		v = v[:i]
	}
	return v
}

func launcherDisplayVersion() string {
	if v := launcherAppVersion(); v != "" {
		return "v" + v
	}
	return "Dungeon World Online"
}

func setReady(port int, attached bool) {
	addrs := fetchNetworkAddresses(port)
	mu.Lock()
	serverPort = port
	roomToRestore := activeRoom
	st = statusState{Phase: "ready", Message: "호스트 서버가 실행 중입니다.", Ready: true, Running: true, Port: port, LocalURL: fmt.Sprintf("http://127.0.0.1:%d", port), LAN: addrs, Attached: attached}
	healthMisses = 0
	healthSuccesses = 0
	intentionalStop = false
	mu.Unlock()
	if roomToRestore != "" {
		go func(room string) { _ = activateCampaign(fmt.Sprintf("http://127.0.0.1:%d", port), room) }(roomToRestore)
	}
}

func fetchNetworkAddresses(port int) []networkAddress {
	var out struct {
		Addresses []networkAddress `json:"addresses"`
	}
	if getJSON(fmt.Sprintf("http://127.0.0.1:%d/api/local/network-info", port), &out, 1200*time.Millisecond) == nil {
		return out.Addresses
	}
	return nil
}

func startDiscoveryResponder() {
	discoveryOnce.Do(func() { go discoveryResponderLoop() })
}

func discoveryResponderLoop() {
	for {
		conn, err := net.ListenUDP("udp4", &net.UDPAddr{IP: net.IPv4zero, Port: discoveryPort})
		if err != nil {
			time.Sleep(2 * time.Second)
			continue
		}
		buf := make([]byte, 2048)
		for {
			_ = conn.SetReadDeadline(time.Now().Add(3 * time.Second))
			n, remote, err := conn.ReadFromUDP(buf)
			if err != nil {
				if ne, ok := err.(net.Error); ok && ne.Timeout() {
					continue
				}
				break
			}
			if strings.TrimSpace(string(buf[:n])) != "DW2_DISCOVER" {
				continue
			}
			mu.Lock()
			ready, port := st.Ready && st.Running, serverPort
			mu.Unlock()
			if !ready || port <= 0 {
				continue
			}
			active := localActiveCampaign(port)
			if !active.Active || active.RoomCode == "" {
				continue
			}
			campaigns := []campaignInfo{{Code: active.RoomCode, CampaignName: active.CampaignName, GMName: active.GMName, PlayerCount: active.PlayerCount, MaxPlayers: active.MaxPlayers}}
			payload, _ := json.Marshal(discoveryResponse{Magic: "DW2", Version: version, Build: embeddedBuildID(), Instance: active.Instance, Port: port, Campaigns: campaigns})
			_, _ = conn.WriteToUDP(payload, remote)
		}
		_ = conn.Close()
		time.Sleep(700 * time.Millisecond)
	}
}

func localActiveCampaign(port int) activeCampaignInfo {
	var out activeCampaignInfo
	if getJSON(fmt.Sprintf("http://127.0.0.1:%d/api/local/active-campaign", port), &out, 800*time.Millisecond) != nil {
		return activeCampaignInfo{}
	}
	return out
}

func discoverLAN(wait time.Duration) []discoveryCampaign {
	conn, err := net.ListenUDP("udp4", &net.UDPAddr{IP: net.IPv4zero, Port: 0})
	if err != nil {
		return nil
	}
	defer conn.Close()
	_ = conn.SetWriteBuffer(64 * 1024)
	targets := []*net.UDPAddr{{IP: net.IPv4bcast, Port: discoveryPort}}
	for _, iface := range interfaceBroadcasts() {
		targets = append(targets, &net.UDPAddr{IP: iface, Port: discoveryPort})
	}
	unique := make([]*net.UDPAddr, 0, len(targets))
	seenTarget := map[string]bool{}
	for _, t := range targets {
		if !seenTarget[t.String()] {
			seenTarget[t.String()] = true
			unique = append(unique, t)
		}
	}
	deadline := time.Now().Add(wait)
	go func() {
		for _, pause := range []time.Duration{0, 350 * time.Millisecond, 700 * time.Millisecond, 1200 * time.Millisecond} {
			if pause > 0 {
				time.Sleep(pause)
			}
			if time.Now().After(deadline) {
				return
			}
			for _, t := range unique {
				_, _ = conn.WriteToUDP([]byte("DW2_DISCOVER"), t)
			}
		}
	}()
	_ = conn.SetReadDeadline(deadline)
	found := map[string]discoveryCampaign{}
	buf := make([]byte, 65535)
	for {
		n, addr, err := conn.ReadFromUDP(buf)
		if err != nil {
			break
		}
		var resp discoveryResponse
		if json.Unmarshal(buf[:n], &resp) != nil || resp.Magic != "DW2" || resp.Version != version || resp.Build != embeddedBuildID() || resp.Port <= 0 {
			continue
		}
		host := fmt.Sprintf("http://%s:%d", addr.IP.String(), resp.Port)
		for _, c := range resp.Campaigns {
			identity := strings.TrimSpace(resp.Instance)
			if identity == "" {
				identity = addr.IP.String() + fmt.Sprintf(":%d", resp.Port)
			}
			key := identity + "|" + strings.ToUpper(c.Code)
			candidate := discoveryCampaign{Host: host, Port: resp.Port, Room: c.Code, CampaignName: c.CampaignName, GMName: c.GMName, PlayerCount: c.PlayerCount, MaxPlayers: c.MaxPlayers, Full: c.PlayerCount >= c.MaxPlayers && c.MaxPlayers > 0}
			if prev, ok := found[key]; !ok || hostPreference(candidate.Host) > hostPreference(prev.Host) {
				found[key] = candidate
			}
		}
	}
	// UDP 응답만 믿지 않고 실제 HTTP/빌드/캠페인 정보를 다시 확인한다.
	verified := make(chan discoveryCampaign, len(found))
	var wg sync.WaitGroup
	for _, x := range found {
		x := x
		wg.Add(1)
		go func() {
			defer wg.Done()
			info, err := probeCampaign(x.Host, x.Room, 950*time.Millisecond)
			if err != nil {
				return
			}
			x.CampaignName = info.CampaignName
			x.GMName = info.GMName
			x.PlayerCount = info.PlayerCount
			x.MaxPlayers = info.MaxPlayers
			x.Full = info.Full
			verified <- x
		}()
	}
	wg.Wait()
	close(verified)
	out := make([]discoveryCampaign, 0, len(found))
	for x := range verified {
		out = append(out, x)
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].CampaignName == out[j].CampaignName {
			return out[i].Host < out[j].Host
		}
		return out[i].CampaignName < out[j].CampaignName
	})
	return out
}

func hostPreference(raw string) int {
	u, err := url.Parse(raw)
	if err != nil {
		return 0
	}
	ip := net.ParseIP(u.Hostname()).To4()
	if ip == nil {
		return 0
	}
	if ip[0] == 192 && ip[1] == 168 {
		return 5
	}
	if ip[0] == 10 || (ip[0] == 172 && ip[1] >= 16 && ip[1] <= 31) {
		return 4
	}
	if ip[0] == 100 && ip[1] >= 64 && ip[1] <= 127 {
		return 3
	}
	if ip[0] == 25 {
		return 2
	}
	return 1
}

func interfaceBroadcasts() []net.IP {
	out := []net.IP{}
	ifs, _ := net.Interfaces()
	for _, iface := range ifs {
		if iface.Flags&net.FlagUp == 0 || iface.Flags&net.FlagLoopback != 0 {
			continue
		}
		addrs, _ := iface.Addrs()
		for _, a := range addrs {
			ipnet, ok := a.(*net.IPNet)
			if !ok {
				continue
			}
			ip := ipnet.IP.To4()
			mask := ipnet.Mask
			if ip == nil || len(mask) != 4 {
				continue
			}
			b := net.IPv4(ip[0]|^mask[0], ip[1]|^mask[1], ip[2]|^mask[2], ip[3]|^mask[3])
			out = append(out, b)
		}
	}
	return out
}

func discoverRoom(room string, wait time.Duration) string {
	for _, x := range discoverLAN(wait) {
		if strings.EqualFold(x.Room, room) {
			return x.Host
		}
	}
	return ""
}

func configRoot() string {
	if custom := strings.TrimSpace(os.Getenv("DW_LAUNCHER_DATA")); custom != "" {
		return custom
	}
	base, err := os.UserConfigDir()
	if err != nil {
		base = os.TempDir()
	}

	current := filepath.Join(base, "DungeonWorldOnline")
	legacy := filepath.Join(base, "DungeonWorldBeta")
	if _, err := os.Stat(current); err == nil {
		return current
	}
	if _, err := os.Stat(legacy); err == nil {
		// Preserve campaigns from development builds by migrating the old data directory once.
		if err := os.Rename(legacy, current); err == nil {
			return current
		}
		// If migration is blocked (for example by permissions), keep using the old directory
		// rather than risking data loss.
		return legacy
	}
	return current
}

func preparePayload() (string, string, error) {
	root := configRoot()
	appDir := filepath.Join(root, "app", version)
	dataDir := filepath.Join(root, "data")
	if err := os.MkdirAll(dataDir, 0755); err != nil {
		return "", "", err
	}
	b, err := decryptedPayload()
	if err != nil {
		return "", "", err
	}
	digest := sha256.Sum256(b)
	payloadHash := hex.EncodeToString(digest[:])
	marker := filepath.Join(appDir, ".payload_sha256")
	if old, err := os.ReadFile(marker); err == nil && strings.TrimSpace(string(old)) == payloadHash {
		cleanupOldPayloads(root, appDir)
		return appDir, dataDir, nil
	}
	_ = os.RemoveAll(appDir)
	if err := os.MkdirAll(appDir, 0755); err != nil {
		return "", "", err
	}
	zr, err := zip.NewReader(bytes.NewReader(b), int64(len(b)))
	if err != nil {
		return "", "", err
	}
	for _, f := range zr.File {
		clean := filepath.Clean(f.Name)
		if clean == "." || strings.HasPrefix(clean, "..") || filepath.IsAbs(clean) {
			return "", "", fmt.Errorf("payload 안에 잘못된 경로가 있습니다.")
		}
		target := filepath.Join(appDir, clean)
		rel, err := filepath.Rel(appDir, target)
		if err != nil || strings.HasPrefix(rel, "..") {
			return "", "", fmt.Errorf("payload 경로를 안전하게 추출할 수 없습니다.")
		}
		if f.FileInfo().IsDir() {
			_ = os.MkdirAll(target, 0755)
			continue
		}
		if err := os.MkdirAll(filepath.Dir(target), 0755); err != nil {
			return "", "", err
		}
		rc, err := f.Open()
		if err != nil {
			return "", "", err
		}
		out, err := os.Create(target)
		if err != nil {
			_ = rc.Close()
			return "", "", err
		}
		_, cpErr := io.Copy(out, rc)
		_ = out.Close()
		_ = rc.Close()
		if cpErr != nil {
			return "", "", cpErr
		}
	}
	if err := os.WriteFile(marker, []byte(payloadHash), 0644); err != nil {
		return "", "", err
	}
	cleanupOldPayloads(root, appDir)
	return appDir, dataDir, nil
}

func cleanupOldPayloads(root, current string) {
	apps := filepath.Join(root, "app")
	entries, err := os.ReadDir(apps)
	if err != nil {
		return
	}
	keep := filepath.Clean(current)
	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}
		candidate := filepath.Join(apps, entry.Name())
		if filepath.Clean(candidate) != keep {
			_ = os.RemoveAll(candidate)
		}
	}
}

func findPython() (pyCommand, error) {
	var cs []pyCommand
	if p, err := exec.LookPath("py.exe"); err == nil {
		cs = append(cs, pyCommand{Exe: p, Args: []string{"-3"}})
	}
	if p, err := exec.LookPath("python.exe"); err == nil {
		cs = append(cs, pyCommand{Exe: p})
	}
	if p, err := exec.LookPath("python"); err == nil {
		cs = append(cs, pyCommand{Exe: p})
	}
	home, _ := os.UserHomeDir()
	if home != "" {
		ms, _ := filepath.Glob(filepath.Join(home, "AppData", "Local", "Programs", "Python", "Python3*", "python.exe"))
		for i := len(ms) - 1; i >= 0; i-- {
			cs = append(cs, pyCommand{Exe: ms[i]})
		}
	}
	for _, c := range cs {
		if runPython(c, "", "-c", "import sys; assert sys.version_info >= (3,11)") == nil {
			return c, nil
		}
	}
	return pyCommand{}, fmt.Errorf("지원되는 Python 실행 파일 없음")
}

func runPython(py pyCommand, dir string, args ...string) error {
	all := append(append([]string{}, py.Args...), args...)
	cmd := exec.Command(py.Exe, all...)
	cmd.Dir = dir
	cmd.Env = append(os.Environ(), "PYTHONUTF8=1")
	hideProcess(cmd)
	return cmd.Run()
}

func getJSON(endpoint string, out any, timeout time.Duration) error {
	status, err := getJSONStatus(endpoint, out, timeout)
	if err != nil {
		return err
	}
	if status < 200 || status >= 300 {
		return fmt.Errorf("HTTP %d", status)
	}
	return nil
}

func getJSONStatus(endpoint string, out any, timeout time.Duration) (int, error) {
	c := http.Client{Timeout: timeout}
	resp, err := c.Get(endpoint)
	if err != nil {
		return 0, err
	}
	defer resp.Body.Close()
	if out != nil {
		_ = json.NewDecoder(resp.Body).Decode(out)
	}
	return resp.StatusCode, nil
}

func postJSON(endpoint string, body any, token string, out any, timeout time.Duration) (int, error) {
	b, _ := json.Marshal(body)
	req, err := http.NewRequest(http.MethodPost, endpoint, bytes.NewReader(b))
	if err != nil {
		return 0, err
	}
	req.Header.Set("Content-Type", "application/json")
	if token != "" {
		req.Header.Set("Authorization", "Bearer "+token)
	}
	c := http.Client{Timeout: timeout}
	resp, err := c.Do(req)
	if err != nil {
		return 0, err
	}
	defer resp.Body.Close()
	if out != nil {
		_ = json.NewDecoder(resp.Body).Decode(out)
	}
	return resp.StatusCode, nil
}

func httpErr(status int, err error, fallback string) string {
	if err != nil {
		return fallback + " " + err.Error()
	}
	if status > 0 {
		return fmt.Sprintf("%s (HTTP %d)", fallback, status)
	}
	return fallback
}

func setStatus(phase, msg string, ready, running bool, port int, errorText string) {
	mu.Lock()
	st.Phase, st.Message, st.Ready, st.Running, st.Port, st.Error = phase, msg, ready, running, port, errorText
	mu.Unlock()
}

func fail(err error) {
	mu.Lock()
	st = statusState{Phase: "error", Message: "실행 중 문제가 발생했습니다.", Error: err.Error()}
	serverPort = 0
	mu.Unlock()
}

func writeJSON(w http.ResponseWriter, v any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.Header().Set("Cache-Control", "no-store")
	_ = json.NewEncoder(w).Encode(v)
}

func recentPath() string {
	root := configRoot()
	_ = os.MkdirAll(root, 0755)
	return filepath.Join(root, "client_recent_v2.json")
}

func loadRecentClients() []recentClient {
	b, err := os.ReadFile(recentPath())
	if err != nil {
		return []recentClient{}
	}
	var x []recentClient
	if json.Unmarshal(b, &x) != nil {
		return []recentClient{}
	}
	if len(x) > 20 {
		x = x[:20]
	}
	return x
}

func writeRecentClients(xs []recentClient) {
	if len(xs) > 20 {
		xs = xs[:20]
	}
	b, _ := json.MarshalIndent(xs, "", "  ")
	_ = os.WriteFile(recentPath(), b, 0600)
}

func saveRecentClient(r recentClient) {
	xs := loadRecentClients()
	out := []recentClient{r}
	for _, x := range xs {
		if strings.EqualFold(x.Host, r.Host) && strings.EqualFold(x.Room, r.Room) {
			continue
		}
		out = append(out, x)
		if len(out) >= 20 {
			break
		}
	}
	writeRecentClients(out)
}

func findRecentClient(host, room string) (recentClient, bool) {
	for _, x := range loadRecentClients() {
		if strings.EqualFold(x.Host, host) && strings.EqualFold(x.Room, room) {
			return x, true
		}
	}
	return recentClient{}, false
}

func removeRecentClient(host, room string) {
	xs := loadRecentClients()
	out := make([]recentClient, 0, len(xs))
	for _, x := range xs {
		if strings.EqualFold(x.Host, host) && strings.EqualFold(x.Room, room) {
			continue
		}
		out = append(out, x)
	}
	writeRecentClients(out)
}

func openBrowser(u string) {
	if runtime.GOOS == "windows" {
		_ = exec.Command("rundll32", "url.dll,FileProtocolHandler", u).Start()
		return
	}
	_ = exec.Command("xdg-open", u).Start()
}

const launcherHTML = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Dungeon World __DISPLAY_VERSION__ Launcher</title><style>
*{box-sizing:border-box}body{margin:0;background:#d7d7d1;color:#111;font-family:"Malgun Gothic",system-ui,sans-serif}.wrap{max-width:1160px;margin:26px auto;padding:16px}.box{background:#f7f6f1;border:4px solid #111;box-shadow:9px 9px 0 #777}.head{background:#111;color:#fff;padding:22px;border-bottom:5px solid #555}.head h1{margin:0;font-family:Georgia,serif;font-size:31px;letter-spacing:.03em}.badge{display:inline-block;background:#fff;color:#111;border:2px solid #fff;padding:5px 9px;font:900 11px system-ui;margin-left:8px}.head p{margin:8px 0 0;color:#ddd}.headtop{display:flex;justify-content:space-between;gap:10px;align-items:center}.langpick{border:2px solid #fff;background:#111;color:#fff;padding:7px 10px;font-weight:900;cursor:pointer}.grid{display:grid;grid-template-columns:1fr 1fr}.card{padding:22px}.card+.card{border-left:3px solid #111}h2{margin:0 0 10px;font-size:27px}h3{margin:14px 0 7px}.btn{min-height:46px;border:3px solid #111;background:#111;color:#fff;font-weight:900;font-size:14px;cursor:pointer;padding:7px 14px}.btn.full{width:100%}.btn.alt{background:#fff;color:#111}.btn.danger{background:#fff;color:#8b1515;border-color:#8b1515}.btn:disabled{opacity:.45;cursor:default}.field{display:grid;gap:5px;margin:9px 0}.field span{font-size:12px;font-weight:900}input,select{min-height:43px;border:2px solid #555;background:#fff;padding:7px;font:inherit}.status{border-top:3px solid #111;padding:16px 22px;background:#fff}.actions{display:flex;gap:7px;flex-wrap:wrap;margin-top:10px}.good{color:#21652d}.bad{color:#8f1717}.small{font-size:12px;color:#555;line-height:1.55}.panel{border:2px solid #111;background:#fff;padding:11px;margin-top:10px}.campaign{display:grid;grid-template-columns:1fr auto;gap:8px;align-items:center;border:2px solid #111;background:#fff;padding:10px;margin:7px 0}.campaign b{font-size:17px}.campaign .actions{margin:0}.recent-title{font-weight:900;margin:12px 0 7px}.online{color:#21652d;font-weight:900}.offline{color:#777;font-weight:900}.hidden{display:none!important}.invite{border:2px dashed #555;padding:8px;margin:7px 0;background:#fff;word-break:break-all}.invite code{font-family:Consolas,monospace;font-size:11px}.step{border-top:2px solid #aaa;margin-top:12px;padding-top:10px}.two{display:grid;grid-template-columns:1fr 1fr;gap:8px}.manage{border-top:3px solid #111;padding:16px 22px;background:#f0efe9}.reconnect{border:3px solid #111;background:#efeee8;padding:10px;margin-top:12px}code{font-family:Consolas,monospace}@media(max-width:780px){.grid{grid-template-columns:1fr}.card+.card{border-left:0;border-top:3px solid #111}.campaign{grid-template-columns:1fr}.two{grid-template-columns:1fr}}</style></head><body><div class="wrap"><div class="box"><div class="head"><div class="headtop"><h1>DUNGEON WORLD <span class="badge">__DISPLAY_VERSION__</span></h1><button id="language" class="langpick" type="button">한국어</button></div><p>호스트나 참가 방식을 선택하면 게임 화면을 브라우저로 엽니다.</p></div><div class="grid"><section class="card"><h2>호스트 · GM</h2><p class="small">캠페인 자료는 이 PC에 저장됩니다. 서버는 자동으로 준비되며, 예기치 않게 멈추면 최대 3회 다시 시작을 시도합니다.</p><button id="hostStart" class="btn full">호스트 서버 시작</button><div id="hostArea" class="hidden"><div id="campaigns"></div><div class="panel"><h3>새 캠페인</h3><label class="field"><span>GM 이름</span><input id="gmName" value="GM"></label><label class="field"><span>캠페인 이름</span><input id="campaignName" value="새 캠페인"></label><label class="field"><span>비밀번호 · 선택</span><input id="campaignPassword" type="password"></label><label class="field"><span>최대 플레이어 · GM 제외</span><select id="campaignMaxPlayers"><option value="2">2명</option><option value="3">3명</option><option value="4" selected>4명 · 기본</option><option value="5">5명</option><option value="6">6명</option><option value="7">7명</option><option value="8">8명</option></select></label><div class="small">캠페인에 동시에 등록할 수 있는 플레이어 정원입니다. GM은 정원에 포함되지 않습니다.</div><button id="createCampaign" class="btn full">새 캠페인 생성</button></div><div id="inviteArea"></div></div></section><section class="card"><h2>플레이어 참가</h2><div id="recent"></div><div class="panel"><h3>LAN에서 찾기</h3><div class="small">검색 요청을 여러 번 보내고 응답한 캠페인을 다시 검증합니다.</div><button id="discover" class="btn alt full">같은 네트워크 캠페인 찾기</button><div id="discovered"></div></div><div class="panel"><h3>새 캠페인 참가</h3><label class="field"><span>초대코드</span><input id="invite" placeholder="DW2-..."></label><div class="small">초대코드가 없다면 아래 주소와 캠페인 코드를 직접 입력할 수 있습니다.</div><div class="two"><label class="field"><span>서버 주소</span><input id="clientHost" placeholder="192.168.0.12:8000"></label><label class="field"><span>캠페인 코드</span><input id="clientRoom" maxlength="6" placeholder="ABC123"></label></div><button id="probe" class="btn full">캠페인 확인</button><div id="joinStep" class="step hidden"><div id="joinInfo" class="small"></div><label class="field"><span>캐릭터 / 표시 이름</span><input id="displayName"></label><label class="field"><span>캠페인 비밀번호</span><input id="joinPassword" type="password"></label><div class="small">처음 참가할 때는 이름과 비밀번호만 입력합니다. 게임 화면에서 직업과 종족을 충분히 살펴본 뒤 선택하게 됩니다.</div><button id="join" class="btn full">참가하고 운명 선택 열기</button></div><div class="reconnect"><h3>기존 캐릭터 재접속 코드</h3><div class="small">같은 LAN에서는 주소 없이도 찾습니다. VPN/다른 집에서는 위의 서버 주소를 함께 입력하세요. 코드는 한 번 사용하면 폐기됩니다.</div><label class="field"><span>재접속 코드</span><input id="reconnectCode" placeholder="ABC123-XXXXXXXX"></label><button id="reconnect" class="btn alt full">기존 캐릭터에 다시 연결</button></div></div></section></div><section class="manage"><b>데이터 관리</b><div class="actions"><button id="clearRecent" class="btn alt">최근 참가 기록 삭제</button><button id="resetBrowser" class="btn alt">브라우저 UI 설정 초기화</button><button id="resetAll" class="btn danger">이 PC의 캠페인 데이터 초기화</button></div></section><div class="status"><b>런처 상태</b><div id="msg">준비됨</div><div id="error" class="bad small"></div><div class="actions"><button id="stop" class="btn alt hidden">서버 종료</button><button id="quit" class="btn alt">런처 종료</button></div></div></div></div><script>
const $=s=>document.querySelector(s),h=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));let last={},probeData=null;const reveal=e=>requestAnimationFrame(()=>e?.scrollIntoView({behavior:'smooth',block:'center'}));
const LKEY='dw_launcher_language_v1';let LANG=localStorage.getItem(LKEY)==='ko'?'ko':'en';
const LEX={
'호스트나 참가 방식을 선택하면 게임 화면을 브라우저로 엽니다.':'The EXE checks the server and connection, then opens the game in your browser.',
'호스트 · GM':'Host · GM','캠페인 자료는 이 PC에 저장됩니다. 서버는 자동으로 준비되며, 예기치 않게 멈추면 최대 3회 다시 시작을 시도합니다.':'Campaign data is stored on this PC. An available port is chosen automatically, and an unexpected server stop is retried up to three times.',
'호스트 서버 시작':'Start Host Server','새 캠페인':'New Campaign','GM':'GM','GM 이름':'GM Name','캠페인 이름':'Campaign Name','비밀번호 · 선택':'Password · Optional','새 캠페인 생성':'Create Campaign','최대 플레이어 · GM 제외':'Maximum Players · GM Excluded','2명':'2 players','3명':'3 players','4명 · 기본':'4 players · Default','5명':'5 players','6명':'6 players','7명':'7 players','8명':'8 players','캠페인에 동시에 등록할 수 있는 플레이어 정원입니다. GM은 정원에 포함되지 않습니다.':'The maximum number of registered player seats for this campaign. The GM does not count toward this limit.','최대 플레이어 수는 2명부터 8명까지 설정할 수 있습니다.':'Maximum players can be set from 2 to 8.','정원 가득 참':'Full',
'플레이어 참가':'Join as Player','LAN에서 찾기':'Find on LAN','검색 요청을 여러 번 보내고 응답한 캠페인을 다시 검증합니다.':'Discovery is sent several times, then responding campaigns are verified.',
'같은 네트워크 캠페인 찾기':'Find Campaigns on This Network','새 캠페인 참가':'Join New Campaign','초대코드':'Invite Code','초대코드가 없다면 아래 주소와 캠페인 코드를 직접 입력할 수 있습니다.':'Without an invite code, enter the server address and campaign code below.',
'서버 주소':'Server Address','캠페인 코드':'Campaign Code','캠페인 확인':'Check Campaign','캐릭터 / 표시 이름':'Character / Display Name','캠페인 비밀번호':'Campaign Password',
'처음 참가할 때는 이름과 비밀번호만 입력합니다. 게임 화면에서 직업과 종족을 충분히 살펴본 뒤 선택하게 됩니다.':'On your first join, enter only your name and password. You can review classes and races in the game before choosing.',
'참가하고 운명 선택 열기':'Join and Choose Your Destiny','기존 캐릭터 재접속 코드':'Existing Character Reconnect Code','같은 LAN에서는 주소 없이도 찾습니다. VPN/다른 집에서는 위의 서버 주소를 함께 입력하세요. 코드는 한 번 사용하면 폐기됩니다.':'On the same LAN, the campaign can be found without an address. Over VPN or another network, enter the server address above. Each code is one-use.',
'재접속 코드':'Reconnect Code','기존 캐릭터에 다시 연결':'Reconnect to Existing Character','데이터 관리':'Data Management','최근 참가 기록 삭제':'Clear Recent Joins','브라우저 UI 설정 초기화':'Reset Browser UI','이 PC의 캠페인 데이터 초기화':'Reset Campaign Data on This PC',
'런처 상태':'Launcher Status','준비됨':'Ready','서버 종료':'Stop Server','런처 종료':'Quit Launcher','이 PC의 캠페인':'Campaigns on This PC','열기':'Open','초대':'Invite','초대 정보':'Invite Information','초대코드 복사':'Copy Invite Code','네트워크':'Network',
'최근 참가한 캠페인':'Recent Campaigns','플레이어':'Player','재접속':'Reconnect','캠페인이 열려 있을 때만 재접속할 수 있습니다.':'Reconnect is available only while the campaign is open.','삭제':'Delete','비밀번호 필요':'Password Required','여러 경로로 찾는 중…':'Searching multiple routes…','선택':'Select','사용 가능한 네트워크 주소를 찾지 못했습니다.':'No usable network address was found.',
'생성 실패':'Creation failed','참가 실패':'Join failed','초기화 실패':'Reset failed','연결 중…':'Connecting…','캠페인을 열지 못했습니다.':'Could not open the campaign.','재접속하지 못했습니다.':'Could not reconnect.','캠페인을 확인하지 못했습니다.':'Could not verify the campaign.','재접속 코드로 연결하지 못했습니다.':'Could not reconnect with that code.',
'로컬 LAN':'Local LAN','네트워크 LAN':'Network LAN','VPN':'VPN','온라인':'Online','오프라인':'Offline',
'비밀번호는 초대코드에 포함되지 않습니다. 친구의 환경에 맞는 코드를 복사하세요.':'The password is not included in the invite code. Copy the code that matches your player’s network.',
'같은 네트워크에서 __DISPLAY_VERSION__ 캠페인을 찾지 못했습니다. 방화벽/VPN 환경에서는 초대코드를 사용하세요.':'No __DISPLAY_VERSION__ campaign was found on this network. If a firewall or VPN is involved, use an invite code.',
'이 캠페인은 현재 열려 있지 않습니다. GM이 캠페인을 연 뒤 다시 시도하세요.':'This campaign is not currently open. Ask the GM to open it and try again.','재접속 인증에 실패했습니다. 인증이 바뀌었다면 새 캠페인 참가 또는 재접속 코드를 이용하세요.':'Reconnect authentication failed. If your credentials changed, join again or use a reconnect code.','캠페인 정원이 가득 찼습니다. GM이 참가자를 정리한 뒤 다시 시도하세요.':'This campaign is full. Ask the GM to free a player slot and try again.','캠페인 정원이 가득 차 있어 이 참가자를 다시 활성화할 수 없습니다.':'This campaign is full, so this participant cannot be re-enabled yet.',
'최근 참가 기록만 삭제할까요?':'Clear only the recent-join history?',
'이 PC의 캠페인 DB와 최근 참가 기록을 삭제합니다. 계속하려면 초기화 를 입력하세요.':'This will delete campaign data on this PC and recent-join history. Type RESET to continue.',
'초기화':'RESET',
'런처 요청 실패: ':'Launcher request failed: ',
'호스트 또는 클라이언트를 선택하세요.':'Choose Host or Client.',
'호스트 서버를 준비하고 있습니다…':'Preparing the host server…',
'캠페인 목록을 읽지 못했습니다: ':'Could not read the campaign list: ',
'GM 이름과 캠페인 이름을 입력하세요.':'Enter a GM name and campaign name.',
'캠페인을 생성하지 못했습니다.':'Could not create the campaign.',
'캠페인 코드가 필요합니다.':'A campaign code is required.',
'호스트 서버를 종료했습니다.':'Host server stopped.',
'캠페인 참가에 실패했습니다.':'Could not join the campaign.',
'이 PC에 해당 캐릭터의 재접속 정보가 없습니다. 새 캠페인 참가를 이용하세요.':'This PC has no reconnect information for that character. Use Join New Campaign instead.',
'재접속하지 못했습니다. 호스트가 실행 중인지 확인하세요. 인증이 바뀌었다면 새 캠페인 참가로 다시 연결해주세요.':'Could not reconnect. Check that the host is running. If authentication changed, join the campaign again.',
'GM에게 받은 재접속 코드를 입력하세요. 예: ABC123-XXXXXXXX':'Enter the reconnect code from the GM, for example ABC123-XXXXXXXX.',
'같은 LAN에서 캠페인을 찾지 못했습니다. VPN/다른 집이라면 서버 주소를 함께 입력하세요.':'The campaign was not found on the same LAN. If you are using a VPN or another network, also enter the server address.',
'재접속 코드가 올바르지 않거나 이미 사용되었습니다.':'The reconnect code is invalid or has already been used.',
'브라우저 초기화를 위해 호스트 서버를 먼저 시작하세요.':'Start the host server before resetting browser settings.',
'캠페인 DB와 최근 참가 기록을 초기화했습니다.':'Campaign data and recent-join history were reset.',
'호스트 서버가 아직 준비되지 않았습니다.':'The host server is not ready yet.',
'캠페인을 온라인 상태로 전환하지 못했습니다.':'Could not bring the campaign online.',
'호스트 주소를 입력하세요.':'Enter the host address.',
'호스트 주소 형식을 확인하세요.':'Check the host address format.',
'http 또는 https 주소만 사용할 수 있습니다.':'Only http or https addresses can be used.',
'Dungeon World 초대코드 형식이 아닙니다.':'This is not a Dungeon World invite code.',
'초대코드를 읽지 못했습니다.':'Could not read the invite code.',
'초대코드 내용이 올바르지 않습니다.':'The invite code contents are invalid.',
'같은 버전의 다른 빌드입니다. GM과 같은 EXE 파일을 사용해주세요.':'This is a different build of the same version. Use the same EXE file as the GM.',
'캠페인 코드를 입력하세요.':'Enter the campaign code.',
'호스트 서버에 연결할 수 없습니다. 주소와 네트워크 연결을 확인하세요.':'Could not connect to the host server. Check the address and network connection.',
'호스트에서 현재 열린 캠페인을 확인하지 못했습니다.':'Could not determine which campaign is currently open on the host.',
'호스트 서버는 실행 중이지만 아직 열린 캠페인이 없습니다.':'The host server is running, but no campaign is open yet.',
'현재 호스트에서 이 캠페인은 열려 있지 않습니다. GM이 해당 캠페인을 열어야 접속할 수 있습니다.':'This campaign is not open on the host. The GM must open it before players can connect.',
'해당 캠페인을 찾을 수 없습니다.':'The campaign could not be found.',
'캠페인 정보를 확인하지 못했습니다.':'Could not verify campaign information.',
'게임 접속 세션을 만들지 못했습니다. 재접속 정보가 만료되었을 수 있습니다.':'Could not create a game session. The reconnect information may have expired.',
'게임 파일을 확인하는 중…':'Checking game files…',
'필수 패키지를 확인하는 중…':'Checking required packages…',
'첫 실행입니다. 필요한 Python 패키지를 설치하는 중…':'First launch: installing the required Python packages…',
'호스트 서버가 종료되었습니다.':'Host server stopped.',
'서버 프로세스가 종료되었습니다.':'The server process exited.',
'서버 응답을 기다리는 중…':'Waiting for the server…',
'호스트 서버 자동 복구를 중단했습니다.':'Automatic host recovery has stopped.',
' 수동으로 호스트 서버를 다시 시작해주세요.':' Restart the host server manually.',
'서버가 연속 3회 상태 확인에 응답하지 않았습니다.':'The server failed three consecutive health checks.',
'연결된 호스트 서버가 더 이상 응답하지 않습니다.':'The connected host server is no longer responding.',
'사용 가능한 서버 포트를 찾지 못했습니다.':'No available server port was found.',
'암호화된 게임 파일 형식이 올바르지 않습니다.':'The encrypted game-file format is invalid.',
'암호화된 게임 파일이 손상되었습니다.':'The encrypted game files are damaged.',
'호스트 서버가 실행 중입니다.':'Host server is running.',
'payload 안에 잘못된 경로가 있습니다.':'The game bundle contains an invalid path.',
'payload 경로를 안전하게 추출할 수 없습니다.':'A game-bundle path could not be extracted safely.',
'지원되는 Python 실행 파일 없음':'No supported Python executable found',
'실행 중 문제가 발생했습니다.':'A problem occurred while running the launcher.'
};
function lt(x){
  if(LANG!=='en')return String(x??'');let v=String(x??'');if(LEX[v])return LEX[v];
  const patterns=[
    [/^서버 버전이 다릅니다\. 초대코드: (.+) \/ 현재 런처: (.+)$/,'Server version mismatch. Invite: $1 / Launcher: $2'],
    [/^서버 버전이 다릅니다\. 서버: (.+) \/ 런처: (.+)$/,'Server version mismatch. Server: $1 / Launcher: $2'],
    [/^같은 (.+)이지만 빌드가 다릅니다\. GM과 같은 EXE 파일을 사용해주세요\.$/,'The version is $1, but the build differs. Use the same EXE file as the GM.'],
    [/^Python 3\.11 이상을 찾지 못했습니다\. \((.*)\)$/,'Python 3.11 or newer was not found. ($1)'],
    [/^필수 패키지 자동 설치 실패: (.*)$/,'Automatic installation of required packages failed: $1'],
    [/^서버 시작 실패: (.*)$/,'Server start failed: $1'],
    [/^서버 프로세스 오류: (.*)$/,'Server process error: $1'],
    [/^서버가 시작되지 않았습니다\. 로그: (.*)$/,'The server did not start. Log: $1'],
    [/^호스트 서버 연결이 끊겨 자동 복구 중입니다\. \((\d+)\/3\)$/,'Host connection was lost. Recovering automatically. ($1/3)'],
    [/^게임 파일 무결성 검증에 실패했습니다: (.*)$/,'Game-file integrity verification failed: $1']
  ];
  for(const [re,repl] of patterns)if(re.test(v))return v.replace(re,repl);
  const pairs=[['캠페인 목록을 읽지 못했습니다: ','Could not read the campaign list: '],['런처 요청 실패: ','Launcher request failed: '],['로컬 LAN','Local LAN'],['네트워크 LAN','Network LAN'],['네트워크','Network'],['비밀번호 필요','Password Required'],['플레이어 ','Player '],['코드 ','Code '],['명',' players'],['초대 정보 · ','Invite Information · '],['GM ','GM ']];for(const [a,b] of pairs)v=v.split(a).join(b);return v
}
function localizeLauncher(root=document.body){
  document.documentElement.lang=LANG==='en'?'en':'ko';
  const base=root?.nodeType===1?root:document.body,w=document.createTreeWalker(base,NodeFilter.SHOW_TEXT),nodes=[];while(w.nextNode())nodes.push(w.currentNode);
  for(const n of nodes){if(n.parentElement?.closest('script,style,code,input'))continue;const raw=n.nodeValue||'';if(n.__dwKoText===undefined&&/[가-힣]/.test(raw))n.__dwKoText=raw;const source=n.__dwKoText!==undefined?n.__dwKoText:raw;if(LANG==='ko'){if(n.__dwKoText!==undefined)n.nodeValue=n.__dwKoText;continue}const m=source.match(/^(\s*)(.*?)(\s*)$/s);if(!m||!m[2])continue;const t=lt(m[2]);n.nodeValue=m[1]+t+m[3]}
  const host=base.querySelectorAll?base:document;host.querySelectorAll?.('input,button,select').forEach(el=>{el.__dwKoAttrs=el.__dwKoAttrs||{};for(const a of ['placeholder','title','aria-label']){const current=el.getAttribute(a);if(current&&el.__dwKoAttrs[a]===undefined&&/[가-힣]/.test(current))el.__dwKoAttrs[a]=current;const source=el.__dwKoAttrs[a];if(source!==undefined)el.setAttribute(a,LANG==='en'?lt(source):source)}if(el.tagName==='INPUT'){if(el.__dwKoValue===undefined&&LEX[el.value])el.__dwKoValue=el.value;if(el.__dwKoValue!==undefined&&(!el.matches(':focus')||el.value===LEX[el.__dwKoValue]||el.value===el.__dwKoValue))el.value=LANG==='en'?lt(el.__dwKoValue):el.__dwKoValue}});
  const languageButton=$('#language'),languageLabel=LANG==='en'?'한국어':'English';
  if(languageButton&&languageButton.textContent!==languageLabel)languageButton.textContent=languageLabel;
}
function gameURL(u){const x=new URL(u,location.href);x.searchParams.set('lang',LANG);return x.toString()}
function openGame(u){const x=gameURL(u),w=window.open(x,'_blank');if(!w)location.href=x}
const mo=new MutationObserver(ms=>{for(const m of ms)for(const n of m.addedNodes)if(n.nodeType===1||n.nodeType===3)localizeLauncher(n.nodeType===3?n.parentElement:n)});mo.observe(document.body,{subtree:true,childList:true});
$('#language').onclick=()=>{LANG=LANG==='en'?'ko':'en';localStorage.setItem(LKEY,LANG);localizeLauncher(document.body)};localizeLauncher();
async function post(u,b){try{const r=await fetch(u,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b||{})}),j=await r.json();return j}catch(e){return {ok:false,error:'런처 요청 실패: '+e.message}}}
async function poll(){try{last=await fetch('/api/status').then(r=>r.json());$('#msg').textContent=lt(last.message||'');$('#error').textContent=lt(last.error||'');$('#hostStart').disabled=last.phase==='starting'||last.running;$('#stop').classList.toggle('hidden',!last.running);$('#hostArea').classList.toggle('hidden',!last.ready);if(last.ready)loadCampaigns()}catch{}setTimeout(poll,900)}
async function loadCampaigns(){try{const x=await fetch('/api/host/campaigns').then(r=>r.json());if(!x.ok)return;$('#campaigns').innerHTML=x.campaigns.length?'<h3>'+h(LANG==='en'?'Campaigns on This PC':'이 PC의 캠페인')+'</h3>'+x.campaigns.map(c=>{const pc=Number(c.player_count||0),mp=Number(c.max_players||4),meta=LANG==='en'?'GM '+h(c.gm_name)+' · Code <b>'+h(c.code)+'</b> · '+pc+'/'+mp+' players':'GM '+h(c.gm_name)+' · 코드 <b>'+h(c.code)+'</b> · 플레이어 '+pc+'/'+mp+'명';return '<div class="campaign"><div><b>'+h(c.campaign_name)+'</b><div class="small">'+meta+'</div></div><div class="actions"><button class="btn" data-host-open="'+h(c.code)+'">'+h(LANG==='en'?'Open':'열기')+'</button><button class="btn alt" data-invite="'+h(c.code)+'">'+h(LANG==='en'?'Invite':'초대')+'</button></div></div>'}).join(''):'';document.querySelectorAll('[data-host-open]').forEach(b=>b.onclick=()=>hostOpen(b.dataset.hostOpen));document.querySelectorAll('[data-invite]').forEach(b=>b.onclick=()=>showInvites(b.dataset.invite))}catch{}}
async function hostOpen(room){const p=window.open('about:blank','_blank'),x=await post('/api/host/open',{room});if(x.ok){if(p)p.location.href=gameURL(x.url);else openGame(x.url);renderInvites(x.invites,x.room)}else{if(p)p.close();$('#error').textContent=lt(x.error)||'캠페인을 열지 못했습니다.'}}
function renderInvites(xs,room){const title=LANG==='en'?'Invite Information':'초대 정보',note=LANG==='en'?'The password is not included in the invite code. Copy the code that matches your player’s network.':'비밀번호는 초대코드에 포함되지 않습니다. 친구의 환경에 맞는 코드를 복사하세요.',fallback=LANG==='en'?'No usable network address was found.':'사용 가능한 네트워크 주소를 찾지 못했습니다.';$('#inviteArea').innerHTML='<div class="panel"><h3>'+h(title)+' · '+h(room)+'</h3><div class="small">'+h(note)+'</div>'+((xs||[]).map((x,i)=>'<div class="invite"><b>'+h(x.kind||(LANG==='en'?'Network':'네트워크'))+' · '+h(x.ip)+'</b><br><code>'+h(x.code)+'</code><div class="actions"><button class="btn alt" data-copy="'+i+'">'+h(LANG==='en'?'Copy Invite Code':'초대코드 복사')+'</button></div></div>').join('')||'<div class="small">'+h(fallback)+'</div>')+'</div>';document.querySelectorAll('[data-copy]').forEach(b=>b.onclick=()=>navigator.clipboard.writeText(xs[Number(b.dataset.copy)].code));reveal($('#inviteArea'))}
async function showInvites(room){const x=await fetch('/api/host/invites?room='+encodeURIComponent(room)).then(r=>r.json());if(x.ok)renderInvites(x.invites,room)}
async function recent(){try{const x=await fetch('/api/recent').then(r=>r.json()),xs=x.recent||[];$('#recent').innerHTML=xs.length?'<div class="recent-title">최근 참가한 캠페인</div>'+xs.map(r=>'<div class="campaign"><div><b>'+h(r.campaign_name||r.room)+'</b><div class="small">'+h(r.display_name||'플레이어')+' · '+h(r.host)+' · <span class="'+(r.online?'online':'offline')+'">'+h(r.status||'')+'</span></div></div><div class="actions"><button class="btn" data-resume="'+h(r.host)+'|'+h(r.room)+'" '+(r.online?'':'disabled title="캠페인이 열려 있을 때만 재접속할 수 있습니다."')+'>재접속</button><button class="btn alt" data-forget="'+h(r.host)+'|'+h(r.room)+'">삭제</button></div></div>').join(''):'';document.querySelectorAll('[data-resume]:not(:disabled)').forEach(b=>b.onclick=()=>{const [host,room]=b.dataset.resume.split('|');resume(host,room)});document.querySelectorAll('[data-forget]').forEach(b=>b.onclick=async()=>{const [host,room]=b.dataset.forget.split('|');await post('/api/recent/delete',{Host:host,Room:room});recent()})}catch{}}
async function resume(host,room){const p=window.open('about:blank','_blank'),x=await post('/api/client/resume',{host,room});if(x.ok){if(p)p.location.href=gameURL(x.url);else openGame(x.url);recent()}else{if(p)p.close();$('#error').textContent=lt(x.error)||'재접속하지 못했습니다.'}}
function fillJoin(info){probeData=info;const pc=Number(info.info.player_count||0),mp=Number(info.info.max_players||4),full=!!info.info.full;$('#joinStep').classList.remove('hidden');$('#joinInfo').innerHTML='<b>'+h(info.info.campaign_name)+'</b> · GM '+h(info.info.gm_name)+' · '+h(LANG==='en'?(pc+'/'+mp+' players'):('플레이어 '+pc+'/'+mp+'명'))+(info.info.password_required?' · '+h(LANG==='en'?'Password Required':'비밀번호 필요'):'')+(full?' · <b class="bad">'+h(LANG==='en'?'Full':'정원 가득 참')+'</b>':'');$('#joinPassword').closest('.field').classList.toggle('hidden',!info.info.password_required);$('#join').disabled=full;$('#join').title=full?(LANG==='en'?'This campaign is full.':'캠페인 정원이 가득 찼습니다.'):'';reveal($('#joinStep'))}
async function probe(){const x=await post('/api/client/probe',{invite:$('#invite').value,host:$('#clientHost').value,room:$('#clientRoom').value});if(x.ok){$('#clientHost').value=x.host;$('#clientRoom').value=x.room;fillJoin(x)}else{$('#joinStep').classList.add('hidden');$('#error').textContent=lt(x.error)||'캠페인을 확인하지 못했습니다.'}}
async function discover(){const d=$('#discovered');d.innerHTML='<div class="small">'+h(LANG==='en'?'Searching multiple routes…':'여러 경로로 찾는 중…')+'</div>';const x=await fetch('/api/discover').then(r=>r.json()),xs=x.campaigns||[];d.innerHTML=xs.length?xs.map(r=>{const pc=Number(r.player_count||0),mp=Number(r.max_players||4),full=!!r.full,meta=LANG==='en'?'GM '+h(r.gm_name)+' · '+h(r.host)+' · '+pc+'/'+mp+' players':'GM '+h(r.gm_name)+' · '+h(r.host)+' · '+pc+'/'+mp+'명';return '<div class="campaign"><div><b>'+h(r.campaign_name)+'</b><div class="small">'+meta+(full?' · <b class="bad">'+h(LANG==='en'?'Full':'정원 가득 참')+'</b>':'')+'</div></div><button class="btn alt" data-found="'+h(r.host)+'|'+h(r.room)+'" '+(full?'disabled':'')+'>'+h(LANG==='en'?'Select':'선택')+'</button></div>'}).join(''):'<div class="small">'+h(LANG==='en'?'No __DISPLAY_VERSION__ campaign was found on this network. If a firewall or VPN is involved, use an invite code.':'같은 네트워크에서 __DISPLAY_VERSION__ 캠페인을 찾지 못했습니다. 방화벽/VPN 환경에서는 초대코드를 사용하세요.')+'</div>';document.querySelectorAll('[data-found]').forEach(b=>b.onclick=()=>{const [host,room]=b.dataset.found.split('|');$('#invite').value='';$('#clientHost').value=host;$('#clientRoom').value=room;probe()})}
async function reconnect(){const p=window.open('about:blank','_blank'),x=await post('/api/client/reconnect',{host:$('#clientHost').value,reconnect_code:$('#reconnectCode').value});if(x.ok){if(p)p.location.href=gameURL(x.url);else openGame(x.url);$('#clientHost').value=x.host||$('#clientHost').value;$('#clientRoom').value=x.room||'';$('#reconnectCode').value='';recent()}else{if(p)p.close();$('#error').textContent=lt(x.error)||'재접속 코드로 연결하지 못했습니다.'}}
$('#hostStart').onclick=()=>post('/api/host');$('#createCampaign').onclick=async()=>{const p=window.open('about:blank','_blank'),x=await post('/api/host/create',{gm_name:$('#gmName').value,campaign_name:$('#campaignName').value,password:$('#campaignPassword').value,max_players:Number($('#campaignMaxPlayers').value)||4});if(x.ok){if(p)p.location.href=gameURL(x.url);else openGame(x.url);renderInvites(x.invites,x.room);loadCampaigns()}else{if(p)p.close();$('#error').textContent=lt(x.error)||'생성 실패'}};$('#probe').onclick=probe;$('#join').onclick=async()=>{if(!probeData)return;const p=window.open('about:blank','_blank'),x=await post('/api/client/join',{host:probeData.host,room:probeData.room,display_name:$('#displayName').value,password:$('#joinPassword').value});if(x.ok){if(p)p.location.href=gameURL(x.url);else openGame(x.url);recent()}else{if(p)p.close();$('#error').textContent=lt(x.error)||'참가 실패'}};$('#discover').onclick=discover;$('#reconnect').onclick=reconnect;$('#stop').onclick=()=>post('/api/stop');$('#clearRecent').onclick=async()=>{if(confirm(lt('최근 참가 기록만 삭제할까요?'))){await post('/api/recent/clear');recent()}};$('#resetBrowser').onclick=async()=>{const x=await post('/api/reset/browser');if(x.ok)openGame(x.url);else $('#error').textContent=lt(x.error)||'초기화 실패'};$('#resetAll').onclick=async()=>{if(prompt(lt('이 PC의 캠페인 DB와 최근 참가 기록을 삭제합니다. 계속하려면 초기화 를 입력하세요.'))===(LANG==='en'?'RESET':'초기화')){await post('/api/reset/all');recent();$('#campaigns').innerHTML=''}};$('#quit').onclick=async()=>{await post('/api/quit');window.close()};recent();setInterval(recent,9000);poll();
</script></body></html>`
