package com.lawcompass.mobiletest;

import android.os.Bundle;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(MlKitObjectDetectorPlugin.class);
        super.onCreate(savedInstanceState);
    }
}
