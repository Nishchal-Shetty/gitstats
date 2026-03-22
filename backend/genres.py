GENRES: dict[str, list[str]] = {
    "web_frontend": [
        "react", "vue", "angular", "svelte", "nextjs", "nuxt", "astro",
        "css", "sass", "tailwind", "styled-components", "css-modules",
        "ui", "design-system", "component-library", "storybook",
        "typescript", "javascript", "webpack", "vite", "spa", "pwa",
        "accessibility", "responsive-design", "animation", "d3",
    ],
    "web_backend": [
        "api", "rest", "graphql", "grpc", "websocket", "rpc",
        "microservices", "monolith", "serverless", "middleware",
        "authentication", "authorization", "oauth", "jwt",
        "database", "orm", "sql", "nosql", "caching", "redis",
        "nodejs", "python", "go", "java", "rust", "ruby", "php",
        "fastapi", "django", "flask", "express", "nestjs", "spring",
        "rate-limiting", "logging", "tracing", "queue", "async",
    ],
    "mobile": [
        "ios", "android", "react-native", "flutter", "swift", "kotlin",
        "cross-platform", "expo", "xamarin", "capacitor", "ionic",
        "mobile-ui", "push-notifications", "offline-first",
        "app-store", "play-store", "biometrics", "geolocation",
        "camera", "bluetooth", "nfc",
    ],
    "devtools": [
        "cli", "ide", "ide-plugin", "vscode-extension", "linter",
        "formatter", "prettier", "eslint", "build-tool", "bundler",
        "compiler", "transpiler", "code-generation", "scaffolding",
        "testing", "unit-testing", "e2e-testing", "mocking",
        "debugging", "profiling", "benchmarking", "documentation",
        "git", "version-control", "package-manager", "monorepo",
        "task-runner", "repl", "language-server",
    ],
    "data_science": [
        "machine-learning", "deep-learning", "neural-network",
        "nlp", "computer-vision", "reinforcement-learning",
        "data-analysis", "data-visualization", "statistics",
        "jupyter", "notebook", "pandas", "numpy", "scipy",
        "tensorflow", "pytorch", "sklearn", "huggingface",
        "etl", "data-pipeline", "feature-engineering",
        "time-series", "anomaly-detection", "recommendation",
        "llm", "rag", "embedding", "vector-database",
    ],
    "infrastructure": [
        "docker", "kubernetes", "helm", "terraform", "ansible",
        "pulumi", "cloudformation", "ci-cd", "github-actions",
        "jenkins", "gitlab-ci", "monitoring", "observability",
        "prometheus", "grafana", "alerting", "logging", "tracing",
        "cloud", "aws", "gcp", "azure", "cdn", "load-balancer",
        "service-mesh", "istio", "nginx", "proxy", "vpn",
        "disaster-recovery", "backup", "scaling", "infrastructure-as-code",
    ],
    "security": [
        "cryptography", "encryption", "hashing", "tls", "ssl",
        "penetration-testing", "vulnerability-scanning", "fuzzing",
        "authentication", "authorization", "zero-trust", "rbac",
        "secrets-management", "key-management", "pki", "certificate",
        "firewall", "ids", "siem", "threat-detection", "malware-analysis",
        "reverse-engineering", "ctf", "audit", "compliance",
        "oauth", "saml", "mfa", "password-manager", "steganography",
    ],
    "game_dev": [
        "unity", "unreal", "godot", "game-engine", "opengl", "vulkan",
        "directx", "webgl", "graphics", "rendering", "shader",
        "physics-engine", "simulation", "2d", "3d", "vr", "ar",
        "multiplayer", "networking", "game-ai", "pathfinding",
        "procedural-generation", "ecs", "animation", "audio",
        "level-editor", "tilemap", "pixel-art", "indie-game",
    ],
    "systems": [
        "operating-system", "kernel", "driver", "firmware", "embedded",
        "rtos", "bare-metal", "arm", "x86", "risc-v", "wasm",
        "compiler", "interpreter", "runtime", "virtual-machine", "jit",
        "memory-management", "garbage-collection", "allocator",
        "concurrency", "threading", "async-runtime", "ipc",
        "file-system", "networking-stack", "protocol", "parser",
        "ffi", "bindings", "low-level", "performance", "simd",
    ],
    "open_source_lib": [
        "sdk", "framework", "utility", "helper", "wrapper", "integration",
        "plugin", "extension", "addon", "middleware", "adapter",
        "client-library", "api-client", "bindings", "interop",
        "zero-dependency", "lightweight", "isomorphic", "cross-platform",
        "well-tested", "typed", "documented", "composable", "modular",
    ],
}

GENRE_DESCRIPTIONS: dict[str, str] = {
    "web_frontend": (
        "A repository focused on browser-based user interfaces, "
        "including UI frameworks, component libraries, design systems, and anything "
        "that runs primarily in the browser and is concerned with visual presentation."
    ),
    "web_backend": (
        "A repository implementing server-side logic, such as REST or GraphQL APIs, "
        "microservices, authentication systems, database layers, or any HTTP server "
        "that handles business logic and data persistence."
    ),
    "mobile": (
        "A repository targeting iOS and/or Android mobile platforms, including native apps, "
        "cross-platform frameworks like React Native or Flutter, and mobile-specific SDKs."
    ),
    "devtools": (
        "A repository that helps developers write, build, test, or maintain code — "
        "including CLIs, linters, formatters, bundlers, code generators, IDE plugins, "
        "test frameworks, and other productivity tools for software development workflows."
    ),
    "data_science": (
        "A repository focused on data analysis, machine learning, deep learning, NLP, "
        "computer vision, data visualization, or any AI/ML pipeline including LLM tooling "
        "and vector databases."
    ),
    "infrastructure": (
        "A repository for managing cloud infrastructure, deployments, and operations — "
        "including container orchestration, IaC tools, CI/CD pipelines, monitoring, "
        "observability, and cloud-provider integrations."
    ),
    "security": (
        "A repository related to cybersecurity, including cryptographic libraries, "
        "authentication/authorization systems, vulnerability scanners, penetration testing "
        "tools, secrets management, and security auditing utilities."
    ),
    "game_dev": (
        "A repository for building games or game-related tooling, including game engines, "
        "rendering engines, physics simulations, shaders, level editors, and multiplayer "
        "networking for interactive entertainment."
    ),
    "systems": (
        "A repository that operates close to the hardware or runtime level, including "
        "operating systems, kernels, compilers, interpreters, runtimes, memory allocators, "
        "embedded firmware, and low-level networking or protocol implementations."
    ),
    "open_source_lib": (
        "A general-purpose library, SDK, or framework intended to be consumed as a "
        "dependency by other projects — including utility helpers, API wrappers, "
        "third-party integrations, and reusable modules not specific to one application domain."
    ),
}

ALL_GENRES: list[str] = list(GENRES.keys())

ALL_TAGS: list[str] = sorted(
    {tag for tags in GENRES.values() for tag in tags}
)
