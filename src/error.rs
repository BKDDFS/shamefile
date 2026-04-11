use std::io;

#[derive(thiserror::Error, Debug)]
pub enum ShamefileError {
    #[error("Failed to read shamefile registry")]
    RegistryReadError(#[source] io::Error),

    #[error("Failed to save shamefile registry")]
    RegistryWriteError(io::Error),

    #[error("Failed to parse shamefile registry")]
    RegistryParseError(#[from] serde_yaml::Error),

    #[error("Duplicate entries in registry: {0}")]
    DuplicateEntries(String),

    #[error("Failed to scan directory")]
    ScanError(#[from] io::Error),
}
