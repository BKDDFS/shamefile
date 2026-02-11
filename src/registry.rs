use crate::ShamefileError;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::Path;

#[derive(Debug, Serialize, Deserialize)]
pub struct Registry {
    /// Configuration for the registry (e.g. version)
    #[serde(default)]
    pub config: Config,
    
    /// The list of known suppressions
    #[serde(default)]
    pub entries: Vec<Entry>,
}

#[derive(Debug, Serialize, Deserialize, Default)]
pub struct Config {
    pub version: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Entry {
    pub file: String,
    pub line: usize,
    pub token: String,
    
    pub author: String,
    pub created_at: DateTime<Utc>,
    
    /// The reason why this suppression exists.
    /// If empty, it means justification is missing.
    pub justification: String,
}

impl Registry {
    pub fn new() -> Self {
        Registry {
            config: Config {
                version: "0.1.0".to_string(),
            },
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
