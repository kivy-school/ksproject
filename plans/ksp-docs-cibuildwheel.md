
# make guides for building kivy 2.3.x (kivy2x repo - master) and 3.0.0 (kivy repo - master) in docs..

write a section is ksproject docs about how to use wheelhouse, and use kivy2x and kivy 3.0.0 master as examples
since we going to have bootstraps for those 2 by default...
soo user can modify the build them self and produce right platform wheels..

## kivy2x

should just require to clone https://github.com/kivy-school/kivy2x
cd kivy2x

### ios
cibuildwheel --platform ios --archs all --output-dir ./wheelhouse

### android
export ANDROID_NDK_HOME="~/.kivyschool/android-sdk/ndk/28.2.13676358"
cibuildwheel --platform android --archs all --output-dir ../wheelhouse

### macos
cibuildwheel --platform macos --archs all --output-dir ./wheelhouse
    or
cibuildwheel --archs all --output-dir ./wheelhouse

### linux
cibuildwheel --platform linux --archs all --output-dir ./wheelhouse
    or
cibuildwheel --archs all --output-dir ./wheelhouse

### windows
cibuildwheel --platform windows --archs all --output-dir ./wheelhouse
    or
cibuildwheel --archs all --output-dir ./wheelhouse

## kivy 3.0.0


### ios
export KIVY_DEPS_ROOT=$(pwd)/ios-kivy-dependencies
export CIBW_BEFORE_ALL_IOS=./tools/build_ios_dependencies.sh
cibuildwheel --platform ios --archs all --output-dir ../wheelhouse
uv run ./tools/add-ios-frameworks.py ../wheelhouse

### android
* needs to write the before-all script and also figure out the thorvg part
* renaming thorvg to kivythor or what it was they wanted as...
(also look into if thorvg-cython going to have issues co-existing with the thorvg lib that cython also has..)
* we properly also need post script for making the wheels add SDL3 kivythor components etc to .libs
(ends up merged in site-packages/.libs)

export ANDROID_NDK_HOME="~/.kivyschool/android-sdk/ndk/28.2.13676358"
export CIBW_BEFORE_ALL_ANDROID="./tools/build_android_dependencies.sh"
cibuildwheel --platform macos --archs all --output-dir ./wheelhouse

### macos
export CIBW_BEFORE_ALL_MACOS="./tools/build_macos_dependencies.sh"
cibuildwheel --platform macos --archs all --output-dir ./wheelhouse

### linux
export CIBW_BEFORE_ALL_LINUX="./tools/build_macos_dependencies.sh"
cibuildwheel --platform macos --archs all --output-dir ./wheelhouse


cibuildwheel --platform ios --archs all --output-dir ./wheelhouse

