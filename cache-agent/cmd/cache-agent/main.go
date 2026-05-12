package main

import (
	"log"

	"cache-agent/internal/config"
	"cache-agent/internal/meta"
	"cache-agent/internal/server"
	"cache-agent/internal/service"
)

func main() {
	cfg := config.Default()
	metaStore, err := meta.Open(cfg.MetaDBPath)
	if err != nil {
		log.Fatalf("open metadata store failed: %v", err)
	}
	defer metaStore.Close()

	h := service.NewHandler(cfg, metaStore)
	_ = server.NewGRPCServer(h)

	log.Println("cache-agent initialized. integrate grpc transport and register NotifyChanged/NotifyDeleted handlers.")
}
