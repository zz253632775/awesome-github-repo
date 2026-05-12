package server

import (
	"context"

	"cache-agent/internal/service"
)

type CacheTier int32

const (
	CacheTierUnspecified CacheTier = 0
	CacheTierTmpfs       CacheTier = 1
	CacheTierSSD         CacheTier = 2
)

type NotifyChangedRequest struct {
	Path      string
	MtimeUnix int64
	Size      int64
	EventId   string
	Tier      CacheTier
}

type NotifyDeletedRequest struct {
	Path    string
	EventId string
	Tier    *CacheTier
}

type NotifyResponse struct {
	Accepted bool
	Message  string
}

type GRPCServer struct{ handler *service.Handler }

func NewGRPCServer(h *service.Handler) *GRPCServer { return &GRPCServer{handler: h} }

func (s *GRPCServer) NotifyChanged(ctx context.Context, req *NotifyChangedRequest) (*NotifyResponse, error) {
	tier := service.TierSSD
	if req.Tier == CacheTierTmpfs {
		tier = service.TierTMPFS
	}
	err := s.handler.HandleChanged(ctx, service.ChangedEvent{Path: req.Path, MTimeUnix: req.MtimeUnix, Size: req.Size, EventID: req.EventId, Tier: tier})
	if err != nil {
		return &NotifyResponse{Accepted: false, Message: err.Error()}, nil
	}
	return &NotifyResponse{Accepted: true, Message: "ok"}, nil
}

func (s *GRPCServer) NotifyDeleted(ctx context.Context, req *NotifyDeletedRequest) (*NotifyResponse, error) {
	var tier *service.Tier
	if req.Tier != nil {
		t := service.TierSSD
		if *req.Tier == CacheTierTmpfs {
			t = service.TierTMPFS
		}
		tier = &t
	}
	err := s.handler.HandleDeleted(ctx, service.DeletedEvent{Path: req.Path, EventID: req.EventId, Tier: tier})
	if err != nil {
		return &NotifyResponse{Accepted: false, Message: err.Error()}, nil
	}
	return &NotifyResponse{Accepted: true, Message: "ok"}, nil
}
