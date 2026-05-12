package service

import (
	"context"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"cache-agent/internal/config"
	"cache-agent/internal/meta"
	"cache-agent/internal/store"
)

type Tier string

const (
	TierTMPFS Tier = "tmpfs"
	TierSSD   Tier = "ssd"
)

type ChangedEvent struct {
	Path      string
	MTimeUnix int64
	Size      int64
	EventID   string
	Tier      Tier
}

type DeletedEvent struct {
	Path    string
	EventID string
	Tier    *Tier
}

type Handler struct {
	cfg   config.Config
	meta  *meta.Store
	locks sync.Map
}

func NewHandler(cfg config.Config, m *meta.Store) *Handler { return &Handler{cfg: cfg, meta: m} }

func (h *Handler) HandleChanged(ctx context.Context, e ChangedEvent) error {
	if err := validatePath(e.Path); err != nil { return err }
	if e.EventID != "" {
		ok, _ := h.meta.IsEventProcessed(e.EventID)
		if ok { return nil }
	}
	unlock := h.lockPath(e.Path)
	defer unlock()

	src := filepath.Join(h.cfg.NFSMountPath, e.Path)
	if _, err := os.Stat(src); err != nil { return fmt.Errorf("source not found: %w", err) }

	tier := meta.Tier(e.Tier)
	dst := filepath.Join(h.baseDir(e.Tier), e.Path)
	if err := store.CopyAtomic(src, dst); err != nil { return err }

	rec := meta.FileRecord{Path: e.Path, Tier: tier, CacheFile: dst, Size: e.Size, MTimeUnix: e.MTimeUnix, UpdatedAt: time.Now(), EventID: e.EventID, State: "ready"}
	if err := h.meta.UpsertFile(rec); err != nil { return err }

	if h.cfg.StrictTier {
		other := TierTMPFS
		if e.Tier == TierTMPFS { other = TierSSD }
		_ = h.deleteByTier(e.Path, other)
	}
	if e.EventID != "" { _ = h.meta.MarkEventProcessed(e.EventID, h.cfg.EventTTL) }
	_ = ctx
	return nil
}

func (h *Handler) HandleDeleted(ctx context.Context, e DeletedEvent) error {
	if err := validatePath(e.Path); err != nil { return err }
	if e.EventID != "" {
		ok, _ := h.meta.IsEventProcessed(e.EventID)
		if ok { return nil }
	}
	unlock := h.lockPath(e.Path)
	defer unlock()

	if e.Tier == nil {
		_ = h.deleteByTier(e.Path, TierTMPFS)
		_ = h.deleteByTier(e.Path, TierSSD)
	} else {
		_ = h.deleteByTier(e.Path, *e.Tier)
	}
	if e.EventID != "" { _ = h.meta.MarkEventProcessed(e.EventID, h.cfg.EventTTL) }
	_ = ctx
	return nil
}

func (h *Handler) deleteByTier(path string, tier Tier) error {
	rec, err := h.meta.GetFile(path, meta.Tier(tier))
	if err == nil {
		_ = store.RemoveIfExists(rec.CacheFile)
	}
	_ = h.meta.DeleteFile(path, meta.Tier(tier))
	return nil
}

func (h *Handler) baseDir(tier Tier) string {
	if tier == TierTMPFS { return h.cfg.TmpfsPath }
	return h.cfg.SSDPath
}

func (h *Handler) lockPath(path string) func() {
	muI, _ := h.locks.LoadOrStore(path, &sync.Mutex{})
	mu := muI.(*sync.Mutex)
	mu.Lock()
	return mu.Unlock
}

func validatePath(p string) error {
	if p == "" || strings.HasPrefix(p, "/") || strings.Contains(p, "..") {
		return errors.New("invalid relative path")
	}
	return nil
}
