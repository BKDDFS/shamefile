use crate::registry::Registry;

/// Configurable max suppressions for the project.
/// TODO: Make this configurable in shamefile.yaml.
pub const MAX_SUPPRESSIONS: usize = 1000;

pub struct GameState {
    pub current_hp: usize,
    pub max_hp: usize,
    pub is_legacy_hell: bool,
}

impl GameState {
    pub fn new(registry: &Registry) -> Self {
        let count = registry.entries.len();
        let max_hp = MAX_SUPPRESSIONS;
        let current_hp = max_hp.saturating_sub(count);
        let is_legacy_hell = current_hp == 0;

        Self {
            current_hp,
            max_hp,
            is_legacy_hell,
        }
    }

}
