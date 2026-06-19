//
//  PyLauncher.swift
//
import Python
import PathKit

import OSLog

#if os(iOS)
import UIKit
#endif

typealias PyPointer = UnsafeMutablePointer<PyObject>

typealias SDL_main_func = @convention(c) (_ argc: Int32, _ argv: UnsafeMutablePointer<UnsafeMutablePointer<CChar>?>) -> Int32
typealias SDL_UIKitRunApp = @convention(c) (
    _ argc: Int32,
    _ argv: UnsafeMutablePointer<UnsafeMutablePointer<CChar>?>,
    _ mainFunction: SDL_main_func
) -> Int32

func run_module_as_main(_ name: String) -> Int32 {
    
    guard
        let run_py = "runpy".withCString(PyImport_ImportModule),
        let run_fn = "_run_module_as_main".withCString({PyObject_GetAttrString(run_py, $0)}),
        let module = name.withCString(PyUnicode_FromString)
    else {
        PyErr_Print()
        return -1
    }
    
    defer {
        Py_DecRef(module)
        Py_DecRef(run_fn)
        Py_DecRef(run_py)
        
    }
    
    guard let result  = PyObject_CallOneArg(run_fn, module) else {
        PyErr_Print()
        return -1
    }
    
    Py_DecRef(result)
    
    return 1
}


final class KivyLauncher {
    
    static let shared: KivyLauncher = try! .init()
    
    
    var env: Environment = .init()
    
    let IOS_IS_WINDOWED: Bool = false
    var KIVY_CONSOLELOG: Bool = true
    
    init() throws {
        
    }
    
    func setup() {
        pythonSettings()
        kivySettings()
        #if os(iOS)
        export_orientation()
        #endif
    }
    
    private func pythonSettings() {
        
    }
    
    private func kivySettings() {
        // Kivy environment to prefer some implementation on iOS platform
        #if os(iOS)
        env.KIVY_BUILD = "ios"
        env.KIVY_WINDOW = "sdl2"
        env.KIVY_IMAGE = "imageio,tex,gif,sdl2"
        env.KIVY_AUDIO = "sdl2"
        env.KIVY_GL_BACKEND = "sdl2"
        
        // IOS_IS_WINDOWED=True disables fullscreen and then statusbar is shown
        env.IOS_IS_WINDOWED = IOS_IS_WINDOWED
        #endif
        
        if !KIVY_CONSOLELOG {
            env.KIVY_NO_CONSOLELOG = "1"
        }
    }
    
    func preLaunch() throws {
        kivySettings()
        #if os(iOS)
        export_orientation()
        #endif
    }
    
    func onLaunch() throws -> Int32 {
        guard let app_module_name = Bundle.main.object(forInfoDictionaryKey: "AppModule") as? String else {
            fatalError("Unable to identify app module name.")
        }
        return run_module_as_main(app_module_name)
    }
    
    func onExit() throws {
        
    }
    
    
    
    private func export_orientation() {
        let info = Bundle.main.infoDictionary
        let orientations = info?["UISupportedInterfaceOrientations"] as? [AnyHashable]
        //var result = "KIVY_ORIENTATION="
        var result = ""
        for i in 0..<(orientations?.count ?? 0) {
            var item = orientations?[i] as? String
            item = (item as NSString?)?.substring(from: 22)
            if i > 0 {
                result = result + " "
            }
            result = result + (item ?? "")
        }
        
        #if os(iOS)
        env.KIVY_ORIENTATION = result
        #endif
        
        #if DEBUG
        print("Available orientation: \(result)")
        #endif
    }
    
    #if os(iOS)
    static func SDLmain() -> Int32 {
        guard
            let sdl2Lib = Bundle.main.path(forResource: "Frameworks/SDL2.framework/SDL2", ofType: nil),
            let handle = dlopen(sdl2Lib, RTLD_LAZY | RTLD_GLOBAL),
            let symbol = dlsym(handle, "SDL_UIKitRunApp")
        else {
            return -1
        }
        let uikitrunapp = unsafeBitCast(symbol, to: SDL_UIKitRunApp.self)
        
        var argv: [UnsafeMutablePointer<CChar>?] = []
        
        return uikitrunapp(0, &argv) { _argc, _argv in
            KivyLauncher.run(_argc, _argv)
            return 0
        }
        
    }
    #else
    static func SDLmain() -> Int32 {
        var argv: [UnsafeMutablePointer<CChar>?] = []
        KivyLauncher.run(0, &argv)
        return 0
    }
    #endif
}

func PyStatus_Exception(_ status: PyStatus) -> Bool {
    Python.PyStatus_Exception(status) == 1
}

extension PyStatus {
    var error: String { .init(cString: err_msg) }
}

extension KivyLauncher {
    
    public static func run(_ argc: Int32, _ argv: UnsafeMutablePointer<UnsafeMutablePointer<CChar>?>) {
            let cls = Self.shared
            do {
                try cls.preLaunch()
                try cls.initPython()
                _ = try cls.onLaunch()
                try cls.onExit()
            } catch let other_err {
                print(other_err.localizedDescription)
            }
        }
    
    func crash_dialog(_ details: String) {
        print("Application has crashed!")
        print("========================\n\(details)")
    }
    
    func initPython() throws {
        
        let resourcePath = Bundle.main.resourcePath!//.replacingOccurrences(of: " ", with: "\\ ")
        
        var preconfig = PyPreConfig()
        var config = PyConfig()
        
        var wtmp_str: UnsafeMutablePointer<wchar_t>?
        var app_packages_path_str: UnsafeMutablePointer<wchar_t>?
        
        var status: PyStatus
        
        print("Configuring isolated Python...")
        PyPreConfig_InitIsolatedConfig(&preconfig)
        PyConfig_InitIsolatedConfig(&config)
        
        preconfig.utf8_mode = 1
        
        config.buffered_stdio = 0
        
        config.write_bytecode = 0
        
        config.module_search_paths_set = 1
        
        setenv("LC_CTYPE", "UTF-8", 1)
        
        print("Pre-initializing Python runtime...")
        status = Py_PreInitialize(&preconfig)
        if PyStatus_Exception(status) {
            crash_dialog("Unable to pre-initialize Python interpreter: \(status.error)")
            PyConfig_Clear(&config)
            Py_ExitStatusException(status)
        }
        
        
        let python_home = "\(resourcePath)/python"
        print("PythonHome: \(python_home)")
        wtmp_str = Py_DecodeLocale(python_home, nil)
        var config_home = config.home
        status = PyConfig_SetString(&config, &config_home, wtmp_str)
        config.home = config_home
        if PyStatus_Exception(status) {
            crash_dialog("Unable to set PYTHONHOME: \(status.error)")
            PyConfig_Clear(&config)
            Py_ExitStatusException(status)
        }
        PyMem_RawFree(wtmp_str)
        
        status = PyConfig_Read(&config)
        if PyStatus_Exception(status) {
            crash_dialog("Unable to read site config: \(status.error)")
            PyConfig_Clear(&config)
            Py_ExitStatusException(status)
        }
        
        print("PYTHONPATH:")
        var path = "\(python_home)/lib"
        print(" - \(path)")
        wtmp_str = Py_DecodeLocale(path, nil)
        status = PyWideStringList_Append(&config.module_search_paths, wtmp_str)
        if PyStatus_Exception(status) {
            crash_dialog("Unable to set PYTHONHOME: \(status.error)")
            PyConfig_Clear(&config)
            Py_ExitStatusException(status)
        }
        PyMem_RawFree(wtmp_str)
        
        path = "\(python_home)/lib/lib-dynload"
        print(" - \(path)")
        wtmp_str = Py_DecodeLocale(path, nil)
        status = PyWideStringList_Append(&config.module_search_paths, wtmp_str)
        if PyStatus_Exception(status) {
            crash_dialog("Unable to set PYTHONHOME: \(status.error)")
            PyConfig_Clear(&config)
            Py_ExitStatusException(status)
        }
        PyMem_RawFree(wtmp_str)
        
        path = "\(resourcePath)/app"
        print(" - \(path)")
        wtmp_str = Py_DecodeLocale(path, nil)
        status = PyWideStringList_Append(&config.module_search_paths, wtmp_str)
        if PyStatus_Exception(status) {
            crash_dialog("Unable to set app path: \(status.error)")
            PyConfig_Clear(&config)
            Py_ExitStatusException(status)
        }
        PyMem_RawFree(wtmp_str)
        
        print("Initializing Python runtime...")
        status = Py_InitializeFromConfig(&config)
        if PyStatus_Exception(status) {
            crash_dialog("Unable to initialize Python interpreter: \(status.error)")
            PyConfig_Clear(&config)
            Py_ExitStatusException(status)
        }
        
        path = "\(python_home)/site_packages"
        app_packages_path_str = Py_DecodeLocale(path, nil)
        print("Adding app_packages as site directory: \(path)")
        
        guard let module = PyImport_ImportModule("site") else {
            crash_dialog("Could not import site module")
            exit(-11)
        }
        
        guard let module_attr = PyObject_GetAttrString(module, "addsitedir"), PyCallable_Check(module_attr) == 1 else {
            crash_dialog("Could not access site.addsitedir")
            exit(-12)
        }
        
        guard let app_packages_path = PyUnicode_FromWideChar(app_packages_path_str, wcslen(app_packages_path_str)) else {
            crash_dialog("Could not convert app_packages path to unicode")
            exit(-13)
        }
        PyMem_RawFree(app_packages_path_str)
        
        PyObject_CallOneArg(module_attr, app_packages_path)
        
        if let _ = PyErr_Occurred() {
            crash_dialog("Could not add app_packages directory using site.addsitedir")
            exit(-15)
        }

        print("---------------------------------------------------------------------------")
    }
}


extension KivyLauncher {
    @dynamicMemberLookup
    struct Environment {
        
        subscript(dynamicMember key: String) -> String? {
            get {
                if let result = key.withCString(getenv) {
                    return .init(cString: result)
                }
                return nil
            }
            set {
                _ = key.withCString { _key in
                    setenv(_key, newValue, 1)
                }
            }
        }
        
        subscript(dynamicMember key: String) -> Int? {
            get {
                if let result = key.withCString(getenv) {
                    return .init(String(cString: result))
                }
                return nil
            }
            set {
                key.withCString { _key in
                    if let newValue = newValue {
                        setenv(_key, String(newValue), 1)
                        return
                    }
                    setenv(_key, nil, 1)
                }
            }
        }
        subscript(dynamicMember key: String) -> Bool? {
            get {
                if let result = key.withCString(getenv) {
                    return .init(String(cString: result).lowercased())
                }
                return nil
            }
            set {
                key.withCString { _key in
                    if let newValue = newValue, let boolValue = newValue ? "True" : "False" {
                        setenv(_key, boolValue, 1)
                        return
                    }
                    setenv(_key, nil, 1)
                }
            }
        }
        
    }
}
