use crate::ShamefileError;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;

#[derive(Debug, Serialize, Deserialize)]
pub struct Registry {
    /// Configuration for the registry
    #[serde(default)]
    pub config: Config,

    /// The list of known suppressions
    #[serde(default)]
    pub entries: Vec<Entry>,
}

#[derive(Debug, Default, Serialize, Deserialize)]
pub struct Config {}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Entry {
    pub file: String,
    pub line: u32,
    pub token: String,

    pub author: String,
    pub created_at: DateTime<Utc>,

    /// The reason why this suppression exists.
    /// If empty, it means justification is missing.
    pub why: String,
}

impl Default for Registry {
    fn default() -> Self {
        Self::new()
    }
}

impl Registry {
    pub fn new() -> Self {
        Registry {
            config: Config::default(),
            entries: Vec::new(),
        }
    }

    pub fn load(path: &Path) -> Result<Self, ShamefileError> {
        let content = fs::read_to_string(path).map_err(ShamefileError::RegistryReadError)?;
        let registry: Registry = serde_yaml::from_str(&content)?;
        Ok(registry)
    }

    pub fn save(&self, path: &Path) -> Result<(), ShamefileError> {
        let content = serde_yaml::to_string(self)?;
        fs::write(path, content).map_err(ShamefileError::RegistryReadError)?;
        Ok(())
    }
}
