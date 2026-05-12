package config

import "time"

type Config struct {
	NFSMountPath string
	TmpfsPath    string
	SSDPath      string
	MetaDBPath   string
	StrictTier   bool
	WorkerCount  int
	EventTTL     time.Duration
}

func Default() Config {
	return Config{
		NFSMountPath: "/mnt/nfs_data",
		TmpfsPath:    "/mnt/cache_mem",
		SSDPath:      "/mnt/cache_ssd",
		MetaDBPath:   "/var/lib/cache-agent/meta.db",
		StrictTier:   true,
		WorkerCount:  8,
		EventTTL:     24 * time.Hour,
	}
}
