use std::io;

#[derive(thiserror::Error, Debug)]
pub enum ShamefileError {
    #[error("Failed to read shamefile registry")]
    RegistryReadError(#[source] io::Error),

    #[error("Failed to parse shamefile registry")]
    RegistryParseError(#[from] serde_yaml::Error),

    #[error("Failed to scan directory")]
    ScanError(#[from] io::Error),

    #[error("Failed to compile regex")]
    RegexCompileError(#[from] grep::regex::Error),

    #[error("Error walking directory")]
    IgnoreError(#[from] ignore::Error),
}
