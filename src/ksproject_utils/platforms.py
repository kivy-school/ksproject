


class Platform:
    
    sdk_platform: str

    pip_platform: str
    pip_arch: str

    root: str

    project_path: str

    site_packages: str


    



class AndroidPlatform(Platform):

    sdk_platform = "android"

    # ABI directory name (matches Gradle's `../site_packages/<abi>` reads
    # in gradle_build_files._site_packages_tasks).
    abi: str

    def __init__(self, root: str):
        self.root = root
        self.project_path = f"{root}/project_dist/gradle"

    @property
    def site_packages(self) -> str:
        return f"{self.project_path}/site_packages/{self.abi}"


class AndroidArm64Platform(AndroidPlatform):

    pip_platform = "aarch64-linux-android"
    pip_arch = "arm64_v8a"
    abi = "arm64-v8a"


class AndroidX86_64Platform(AndroidPlatform):

    pip_platform = "x86_64-linux-android"
    pip_arch = "x86_64"
    abi = "x86_64"




class ApplePlatform(Platform):

    sdk_platform = "apple"


    def __init__(self, root: str):
        self.root = root
        self.project_path = f"{root}/project_dist/xcode"

    @property
    def site_packages(self) -> str:
        return f"{self.project_path}/site-packages/{self.pip_platform}"


class IOSArm64Platform(ApplePlatform):

    pip_platform = "arm64-apple-ios"
    pip_arch = "arm64"

class IOSSim_X86_64Platform(ApplePlatform):
    pip_platform = "x86_64-apple-ios-simulator"
    pip_arch = "x86_64"

class IOSSim_Arm64Platform(ApplePlatform):

    pip_platform = "arm64-apple-ios-simulator"
    pip_arch = "arm64"