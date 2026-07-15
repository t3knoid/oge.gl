const defaultApiBaseUrl = "http://127.0.0.1:8000/api/v1";
const defaultManualIngestMode = "incremental";
const defaultManualIngestLimit = 1;

export const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? defaultApiBaseUrl;

export interface ManualIngestDefaults {
	mode: "incremental";
	limit: number;
}

export interface ManualIngestConfigResolution {
	defaults: ManualIngestDefaults;
	error: string | null;
}

export function resolveManualIngestDefaults(
	rawMode: string | undefined,
	rawLimit: string | undefined,
): ManualIngestConfigResolution {
	const mode = rawMode ?? defaultManualIngestMode;
	const limitText = rawLimit ?? String(defaultManualIngestLimit);
	const parsedLimit = Number.parseInt(limitText, 10);

	if (mode !== "incremental") {
		return {
			defaults: { mode: defaultManualIngestMode, limit: defaultManualIngestLimit },
			error: "Manual fetch configuration is invalid. Set VITE_INGEST_RUN_DEFAULT_MODE to incremental.",
		};
	}

	if (Number.isNaN(parsedLimit) || parsedLimit < 1) {
		return {
			defaults: { mode: defaultManualIngestMode, limit: defaultManualIngestLimit },
			error: "Manual fetch configuration is invalid. Set VITE_INGEST_RUN_DEFAULT_LIMIT to a positive integer.",
		};
	}

	return {
		defaults: { mode, limit: parsedLimit },
		error: null,
	};
}

export const manualIngestConfig = resolveManualIngestDefaults(
	import.meta.env.VITE_INGEST_RUN_DEFAULT_MODE,
	import.meta.env.VITE_INGEST_RUN_DEFAULT_LIMIT,
);
