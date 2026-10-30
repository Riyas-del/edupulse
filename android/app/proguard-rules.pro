# EduPulse Proguard Rules
-keepattributes *Annotation*
-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}
-keep class com.edupulse.app.** { *; }
